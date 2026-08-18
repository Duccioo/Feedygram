import os
import re
from typing import Optional, List

DEFAULT_BRIDGES = [
    "https://nitter.net/{username}/rss",
    "https://xcancel.com/{username}/rss",
    "https://nitter.poast.org/{username}/rss",
    "https://openrss.org/twitter.com/{username}",
]


def extract_twitter_username(target: str) -> Optional[str]:
    """
    Estrae l'handle di Twitter/X da input come '@user', 'x.com/user', 'twitter.com/user', ecc.
    """
    target = target.strip()
    if target.startswith("@"):
        username = target[1:]
        if re.match(r"^[A-Za-z0-9_]{1,15}$", username):
            return username

    # Esclude link a singoli tweet
    if "/status/" in target.lower() or "/statuses/" in target.lower():
        return None

    # Regex per URL di Twitter/X
    match = re.search(
        r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([A-Za-z0-9_]{1,15})(?:/|\?.*|$)",
        target,
        re.IGNORECASE,
    )
    if match:
        user = match.group(1)
        # Esclude route riservate di X
        if user.lower() not in ("home", "explore", "notifications", "messages", "search", "i", "settings", "status", "statuses"):
            return user

    return None


def get_twitter_rss_url(username: str) -> str:
    """
    Costruisce l'URL del feed RSS per l'utente X/Twitter usando il bridge configurato.
    """
    custom_bridge = os.environ.get("TWITTER_RSS_BRIDGE")
    if custom_bridge:
        if "{username}" in custom_bridge:
            return custom_bridge.replace("{username}", username)
        return f"{custom_bridge.rstrip('/')}/{username}/rss"

    # Default al primo bridge disponibile
    return DEFAULT_BRIDGES[0].format(username=username)


def get_candidate_twitter_rss_urls(username: str) -> List[str]:
    """
    Restituisce una lista di URL candidati (incluso bridge custom e fallback).
    """
    urls = []
    custom = os.environ.get("TWITTER_RSS_BRIDGE")
    if custom:
        if "{username}" in custom:
            urls.append(custom.replace("{username}", username))
        else:
            urls.append(f"{custom.rstrip('/')}/{username}/rss")

    for template in DEFAULT_BRIDGES:
        formatted = template.format(username=username)
        if formatted not in urls:
            urls.append(formatted)

    return urls


def convert_to_fxtwitter_url(url: str) -> str:
    """
    Converte un link di tweet (x.com, twitter.com, nitter.net, xcancel.com) nel corrispondente
    link fxtwitter.com per generare anteprime multimediali ricche (video/immagini) su Telegram.
    """
    if not url:
        return ""

    # Match /<username>/status/<id> o /<username>/statuses/<id>
    match = re.search(
        r"https?://(?:www\.)?(?:twitter\.com|x\.com|nitter\.[a-z.]+|xcancel\.com)/([^/]+/(?:status|statuses)/\d+)",
        url,
        re.IGNORECASE,
    )
    if match:
        path = match.group(1).replace("/statuses/", "/status/")
        return f"https://fxtwitter.com/{path}"

    return url
