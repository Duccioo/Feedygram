import os
import re
import html
import logging
import requests
from typing import Optional, List

logger = logging.getLogger(__name__)

# Parole di stop comuni (IT / EN) per l'algoritmo di summarization estrattiva
STOP_WORDS = {
    "the", "and", "is", "in", "to", "of", "it", "that", "you", "for", "on", "with", "as",
    "this", "by", "are", "be", "from", "at", "or", "an", "was", "we", "will", "an",
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in", "con",
    "su", "per", "tra", "fra", "e", "ed", "o", "ma", "che", "chi", "cui", "non", "sono",
    "ha", "hanno", "è", "si", "del", "della", "dei", "delle", "al", "alla", "nel", "nella",
}


def _extract_article_text(url: str, fallback_text: str = "") -> str:
    """
    Estrae il testo pulito dell'articolo usando Trafilatura o Jina Reader (entrambi gratuiti).
    """
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted = trafilatura.extract(downloaded)
            if extracted and len(extracted.strip()) > 100:
                return extracted.strip()
    except Exception:
        pass

    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"User-Agent": "Feedygram/1.0"}
        resp = requests.get(jina_url, headers=headers, timeout=6)
        if resp.status_code == 200 and resp.text:
            text = resp.text.strip()
            if len(text) > 100:
                return text
    except Exception:
        pass

    return fallback_text.strip()


def _clean_text(raw: str) -> str:
    """Rimuove tag HTML residui e normalizza whitespace per la sintesi."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extractive_summarize(text: str, max_sentences: int = 3) -> str:
    """
    Algoritmo estrattivo puro (0 RAM, 0ms, 100% offline):
    Calcola la frequenza delle parole chiave e seleziona le 3 frasi più informative.
    """
    cleaned = _clean_text(text)
    # Divide il testo in frasi
    raw_sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 30 and not s.startswith("http")]

    if not sentences:
        return cleaned[:300] + "..." if len(cleaned) > 300 else cleaned

    if len(sentences) <= max_sentences:
        return "\n".join(f"• {s}" for s in sentences)

    # Calcola frequenza parole
    words = re.findall(r"\b[A-Za-zÀ-ÿ]{3,}\b", text.lower())
    freq = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1

    # Assegna punteggio a ciascuna frase (con bonus per le prime frasi dell'articolo)
    scores = []
    for idx, sentence in enumerate(sentences):
        s_words = re.findall(r"\b[A-Za-zÀ-ÿ]{3,}\b", sentence.lower())
        score = sum(freq.get(w, 0) for w in s_words)
        # Position bias: i primi paragrafi contengono le informazioni più importanti
        if idx < 3:
            score *= 1.3
        scores.append((score, idx, sentence))

    # Ordina per punteggio decrescente e prendi le prime N
    scores.sort(key=lambda x: x[0], reverse=True)
    top_sentences = sorted(scores[:max_sentences], key=lambda x: x[1])

    return "\n".join(f"• {item[2]}" for item in top_sentences)


def summarize_article(url: str, title: str = "", summary_text: str = "") -> str:
    """
    Genera un TL;DR conciso per un articolo senza costi o pesanti modelli locali.
    """
    content = _extract_article_text(url, fallback_text=summary_text or title)
    if not content or len(content.strip()) < 40:
        content = summary_text or title

    tldr = _extractive_summarize(content, max_sentences=3)
    return tldr
