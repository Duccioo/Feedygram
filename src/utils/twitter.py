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
    Extracts Twitter/X handle from inputs like '@user', 'x.com/user', 'twitter.com/user', etc.
    """
    target = target.strip()
    if target.startswith("@"):
        username = target[1:]
        if re.match(r"^[A-Za-z0-9_]{1,15}$", username):
            return username

    # Exclude single tweet URLs
    if "/status/" in target.lower() or "/statuses/" in target.lower():
        return None

    # Regex for Twitter/X URLs
    match = re.search(
        r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([A-Za-z0-9_]{1,15})(?:/|\?.*|$)",
        target,
        re.IGNORECASE,
    )
    if match:
        user = match.group(1)
        # Exclude reserved X routes
        if user.lower() not in ("home", "explore", "notifications", "messages", "search", "i", "settings", "status", "statuses"):
            return user

    return None


def get_twitter_rss_url(username: str) -> str:
    """
    Builds the RSS feed URL for the X/Twitter user using configured bridge.
    """
    custom_bridge = os.environ.get("TWITTER_RSS_BRIDGE")
    if custom_bridge:
        if "{username}" in custom_bridge:
            return custom_bridge.replace("{username}", username)
        return f"{custom_bridge.rstrip('/')}/{username}/rss"

    # Default to first available bridge
    return DEFAULT_BRIDGES[0].format(username=username)


def get_candidate_twitter_rss_urls(username: str) -> List[str]:
    """
    Returns candidate URLs list (including custom bridge and fallbacks).
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
    Converts a tweet link (x.com, twitter.com, nitter.net, xcancel.com) to the corresponding
    fxtwitter.com link to generate rich media previews (videos/images) in Telegram.
    """
    if not url:
        return ""

    # Match /<username>/status/<id> or /<username>/statuses/<id>
    match = re.search(
        r"https?://(?:www\.)?(?:twitter\.com|x\.com|nitter\.[a-z.]+|xcancel\.com)/([^/]+/(?:status|statuses)/\d+)",
        url,
        re.IGNORECASE,
    )
    if match:
        path = match.group(1).replace("/statuses/", "/status/")
        return f"https://fxtwitter.com/{path}"

    return url

