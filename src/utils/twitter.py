import json
import logging
import os
import re
from typing import Optional, List, Tuple, Any
from bs4 import BeautifulSoup
import requests

from utils.datehandler import DateHandler

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

DEFAULT_BRIDGES = [
    "https://nitter.net/{username}/rss",
    "https://xcancel.com/{username}/rss",
    "https://nitter.poast.org/{username}/rss",
    "https://openrss.org/twitter.com/{username}",
]


def extract_twitter_username(target: str) -> Optional[str]:
    """
    Extracts Twitter/X handle from inputs like '@user', 'x.com/user', 'twitter.com/user',
    'nitter.net/user/rss', 'xcancel.com/user', 'openrss.org/twitter.com/user', etc.
    """
    if not target:
        return None
    target = target.strip()
    if target.startswith("@"):
        username = target[1:]
        if re.match(r"^[A-Za-z0-9_]{1,15}$", username):
            return username

    # Exclude single tweet URLs
    if "/status/" in target.lower() or "/statuses/" in target.lower():
        return None

    # Match syndication URL
    match_syndication = re.search(
        r"syndication\.twitter\.com/srv/timeline-profile/screen-name/([A-Za-z0-9_]{1,15})",
        target,
        re.IGNORECASE,
    )
    if match_syndication:
        return match_syndication.group(1)

    # Match OpenRSS
    match_openrss = re.search(
        r"openrss\.org/twitter\.com/([A-Za-z0-9_]{1,15})",
        target,
        re.IGNORECASE,
    )
    if match_openrss:
        return match_openrss.group(1)

    # Match Nitter / xcancel / bridge instances
    match_nitter = re.search(
        r"(?:https?://)?(?:www\.)?(?:nitter\.[a-z.]+|xcancel\.com)/([A-Za-z0-9_]{1,15})(?:/.*|$)",
        target,
        re.IGNORECASE,
    )
    if match_nitter:
        user = match_nitter.group(1)
        if user.lower() not in ("about", "search", "settings", "status", "statuses", "home"):
            return user

    # Regex for Twitter/X URLs
    match = re.search(
        r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([A-Za-z0-9_]{1,15})(?:/|\?.*|$)",
        target,
        re.IGNORECASE,
    )
    if match:
        user = match.group(1)
        # Exclude reserved X routes
        if user.lower() not in ("home", "explore", "notifications", "messages", "search", "i", "settings", "status", "statuses", "srv"):
            return user

    return None


def fetch_twitter_syndication_entries(username_or_url: str, limit: int = 0) -> List[Any]:
    """
    Fetches latest tweets directly via Twitter's official syndication timeline endpoint.
    Extracts tweet text, media, permalinks, hashtags, and dates.
    """
    from providers.models import FeedItem

    username = extract_twitter_username(username_or_url) or username_or_url.strip("@")
    if not username:
        return []

    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200 or not resp.text:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return []

        data = json.loads(script.string)
        page_props = data.get("props", {}).get("pageProps", {})
        timeline = page_props.get("timeline", {})
        entries = timeline.get("entries", [])

        items: List[FeedItem] = []
        for entry in entries:
            tweet = entry.get("content", {}).get("tweet")
            if not tweet:
                continue

            tweet_id = str(tweet.get("id_str") or tweet.get("id") or "")
            if not tweet_id:
                continue

            raw_text = tweet.get("full_text") or tweet.get("text") or ""

            # Replace t.co URLs with full expanded display URLs
            entities = tweet.get("entities") or {}
            urls_info = entities.get("urls") or []
            clean_text = raw_text
            for u_info in urls_info:
                short_url = u_info.get("url")
                exp_url = u_info.get("expanded_url") or u_info.get("display_url")
                if short_url and exp_url:
                    clean_text = clean_text.replace(short_url, exp_url)

            user_info = tweet.get("user") or {}
            screen_name = user_info.get("screen_name") or username

            tweet_link = f"https://x.com/{screen_name}/status/{tweet_id}"
            fx_link = f"https://fxtwitter.com/{screen_name}/status/{tweet_id}"

            created_at_raw = tweet.get("created_at")
            parsed_date = DateHandler.parse_datetime(created_at_raw) if created_at_raw else None

            # Extract hashtags
            raw_hashtags = entities.get("hashtags") or []
            tags: List[str] = []
            for h in raw_hashtags:
                h_text = h.get("text") if isinstance(h, dict) else str(h)
                if h_text and str(h_text).strip():
                    tags.append(str(h_text).strip())

            items.append(
                FeedItem(
                    id=tweet_id,
                    title=clean_text,
                    link=tweet_link,
                    published=parsed_date,
                    summary=clean_text,
                    source_link=fx_link,
                    tags=tags,
                )
            )

        if limit > 0:
            return items[:limit]
        return items
    except Exception as e:
        logger.warning(f"Error fetching Twitter syndication for {username}: {e}")
        return []


def validate_twitter_user(username_or_url: str) -> Tuple[bool, Optional[str]]:
    """
    Validates whether a Twitter user exists and has accessible public timeline data.
    """
    username = extract_twitter_username(username_or_url) or username_or_url.strip("@")
    if not username or not re.match(r"^[A-Za-z0-9_]{1,15}$", username):
        return False, "Invalid Twitter username format"

    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return False, f"Twitter syndication returned HTTP {resp.status_code}"

        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return False, "Could not retrieve user timeline data"

        data = json.loads(script.string)
        page_props = data.get("props", {}).get("pageProps", {})
        has_results = page_props.get("contextProvider", {}).get("hasResults", True)
        timeline = page_props.get("timeline", {})
        entries = timeline.get("entries", [])

        if has_results is False and len(entries) == 0:
            return False, f"Twitter account @{username} does not exist or has no public tweets"

        return True, None
    except Exception as e:
        return False, f"Error verifying Twitter account: {e}"


def get_twitter_user_title(username_or_url: str) -> Optional[str]:
    """
    Extracts display name and screen name for a Twitter account (e.g. 'Eric Migicovsky (@ericmigi)').
    """
    username = extract_twitter_username(username_or_url) or username_or_url.strip("@")
    if not username:
        return None

    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200 and resp.text:
            soup = BeautifulSoup(resp.text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if script and script.string:
                data = json.loads(script.string)
                entries = data.get("props", {}).get("pageProps", {}).get("timeline", {}).get("entries", [])
                for e in entries:
                    tweet = e.get("content", {}).get("tweet", {})
                    name = tweet.get("user", {}).get("name")
                    if name:
                        return f"{name} (@{username})"
    except Exception:
        pass
    return f"@{username}"


def get_twitter_rss_url(username: str) -> str:
    """
    Builds the RSS / feed URL for the X/Twitter user using configured bridge or direct X URL.
    """
    custom_bridge = os.environ.get("TWITTER_RSS_BRIDGE")
    if custom_bridge:
        if "{username}" in custom_bridge:
            return custom_bridge.replace("{username}", username)
        return f"{custom_bridge.rstrip('/')}/{username}/rss"

    return f"https://x.com/{username}"


def get_candidate_twitter_rss_urls(username: str) -> List[str]:
    """
    Returns candidate URLs list (including custom bridge, direct X URL, and fallbacks).
    """
    urls = []
    custom = os.environ.get("TWITTER_RSS_BRIDGE")
    if custom:
        if "{username}" in custom:
            urls.append(custom.replace("{username}", username))
        else:
            urls.append(f"{custom.rstrip('/')}/{username}/rss")

    direct_x = f"https://x.com/{username}"
    if direct_x not in urls:
        urls.append(direct_x)

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


