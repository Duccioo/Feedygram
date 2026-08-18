import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

_telegraph_token: Optional[str] = None


def _get_telegraph_poster():
    """Inizializza o recupera l'istanza TelegraphPoster riutilizzando il token"""
    global _telegraph_token
    try:
        from html_telegraph_poster import TelegraphPoster

        poster = TelegraphPoster(use_api=True)
        if _telegraph_token:
            poster.access_token = _telegraph_token
        else:
            poster.create_api_token("Feedygram")
            _telegraph_token = poster.access_token
        return poster
    except Exception as e:
        logger.warning("Impossibile inizializzare TelegraphPoster: %s", str(e))
        return None


def _post_html_to_telegraph(title: str, html_content: str) -> Optional[str]:
    """Pubblica contenuto HTML pulito su Telegraph senza caricamento di immagini esterne"""
    if not html_content or not html_content.strip():
        return None
    try:
        poster = _get_telegraph_poster()
        if poster:
            clean_title = (title or "News Update")[:128]
            try:
                res = poster.post(title=clean_title, author="Feedygram", text=html_content, upload_images=False)
            except TypeError:
                res = poster.post(title=clean_title, author="Feedygram", text=html_content)
            if res and isinstance(res, dict) and "url" in res:
                return str(res["url"])
    except Exception as e:
        logger.warning("Errore pubblicazione su Telegraph: %s", str(e))
    return None


def _try_trafilatura(url: str, title: str = "") -> Optional[str]:
    """
    Tier 1: Estrae l'articolo pulito con Trafilatura (rimuove menu, cookie, sidebar, pubblicità)
    e lo pubblica su Telegraph.
    """
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted_html = trafilatura.extract(
                downloaded,
                output_format="xml",
                include_links=True,
                include_images=True,
                include_formatting=True,
            )
            if extracted_html and len(extracted_html.strip()) > 50:
                # Normalizza i tag XML generati da Trafilatura in HTML per Telegraph
                clean_html = extracted_html.replace("<doc>", "<div>").replace("</doc>", "</div>")
                telegraph_url = _post_html_to_telegraph(title or "Article", clean_html)
                if telegraph_url:
                    logger.info("Conversione Telegraph riuscita tramite Trafilatura: %s", telegraph_url)
                    return telegraph_url
    except Exception as e:
        logger.debug("Tier 1 (Trafilatura) non riuscito per %s: %s", url, str(e))
    return None


def _try_webpage2telegraph(url: str) -> Optional[str]:
    """
    Tier 2: Tenta la conversione tramite webpage2telegraph.
    """
    try:
        import webpage2telegraph

        res = webpage2telegraph.transfer(url)
        if res and str(res).startswith("http") and "telegra.ph" in str(res):
            logger.info("Conversione Telegraph riuscita tramite webpage2telegraph: %s", str(res))
            return str(res)
    except Exception as e:
        logger.debug("Tier 2 (webpage2telegraph) non riuscito per %s: %s", url, str(e))
    return None


def convert_to_instant_link(url: str, title: str = "") -> str:
    """
    Pipeline di conversione Instant View / Telegraph Link:
    1. Tier 1: Trafilatura (estrazione articolo pulito senza navbar/cookie) -> Telegraph
    2. Tier 2: webpage2telegraph -> Telegraph
    3. Fallback Finale: URL originale (evita di restituire markdown grezzo o pagine corrotte)
    """
    if not url:
        return ""

    # 1. Prova Tier 1 (Trafilatura -> Telegraph)
    link = _try_trafilatura(url, title)
    if link:
        return link

    # 2. Fallback Tier 2 (webpage2telegraph)
    link = _try_webpage2telegraph(url)
    if link:
        return link

    # 3. Fallback Finale: URL originale
    logger.info("Conversione Telegraph non disponibile, uso link originale: %s", url)
    return url
