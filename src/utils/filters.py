import re
from typing import List
from providers.models import FeedItem


def matches_filter(entry: FeedItem, filter_rules: str) -> bool:
    """
    Verifica se un FeedItem rispetta le regole di filtro configurate per l'utente.
    Sintassi regole:
    - '+keyword' o 'keyword': l'articolo deve contenere almeno una delle parole positive indicate
    - '-keyword': l'articolo NON deve contenere nessuna delle parole negative indicate
    """
    if not filter_rules or not filter_rules.strip():
        return True

    tags_str = " ".join(entry.tags or [])
    text = f"{entry.title or ''} {entry.summary or ''} {tags_str}".lower()

    tokens = [t.strip() for t in re.split(r"[\s,]+", filter_rules) if t.strip()]
    if not tokens:
        return True

    positive_keywords: List[str] = []
    negative_keywords: List[str] = []

    for t in tokens:
        if t.startswith("-") and len(t) > 1:
            negative_keywords.append(t[1:].lower())
        elif t.startswith("+") and len(t) > 1:
            positive_keywords.append(t[1:].lower())
        else:
            positive_keywords.append(t.lower())

    # Se è presente una parola negativa -> scarta
    for neg in negative_keywords:
        if neg in text:
            return False

    # Se sono definite parole positive -> deve contenerne almeno una
    if positive_keywords:
        if not any(pos in text for pos in positive_keywords):
            return False

    return True
