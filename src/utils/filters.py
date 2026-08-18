import re
from typing import List
from providers.models import FeedItem


def matches_filter(entry: FeedItem, filter_rules: str) -> bool:
    """
    Checks if a FeedItem matches keyword filter rules configured for the user.
    Rule syntax:
    - '+keyword' or 'keyword': article must contain at least one of the positive keywords
    - '-keyword': article must NOT contain any of the negative keywords
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

    # If any negative keyword matches -> reject
    for neg in negative_keywords:
        if neg in text:
            return False

    # If positive keywords are defined -> must contain at least one
    if positive_keywords:
        if not any(pos in text for pos in positive_keywords):
            return False

    return True

