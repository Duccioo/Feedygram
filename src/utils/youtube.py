import re
import urllib.request
import logging
from typing import Optional

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"


def extract_youtube_channel_id(url_or_handle: str) -> Optional[str]:
    """
    Resolves YouTube URL or handle (@username, /channel/UC..., /user/...) to channel ID (UC...).
    """
    target = url_or_handle.strip()

    # 1. Already a direct channel_id (e.g. UC...)
    if re.match(r"^UC[a-zA-Z0-9_-]{22}$", target):
        return target

    # 2. Direct channel URL: youtube.com/channel/UC...
    match_channel = re.search(r"youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})", target, re.IGNORECASE)
    if match_channel:
        return match_channel.group(1)

    # 3. Handle @username or URL with @ or /c/ or /user/
    handle = None
    if target.startswith("@"):
        handle = target
    else:
        match_handle = re.search(r"youtube\.com/(?:c/|user/)?(@?[a-zA-Z0-9_.-]+)", target, re.IGNORECASE)
        if match_handle:
            val = match_handle.group(1)
            if val.lower() not in ("watch", "playlist", "feed", "channel", "results", "live"):
                handle = val

    if handle:
        # Fetch channel page and extract channel_id via regex from HTML
        channel_url = f"https://www.youtube.com/{handle}" if not handle.startswith("http") else handle
        try:
            req = urllib.request.Request(channel_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as resp:
                html_text = resp.read().decode("utf-8", errors="ignore")
                match_id = re.search(r'channelId":"(UC[a-zA-Z0-9_-]{22})"', html_text)
                if match_id:
                    return match_id.group(1)
                match_id_alt = re.search(r'itemprop="channelId" content="(UC[a-zA-Z0-9_-]{22})"', html_text)
                if match_id_alt:
                    return match_id_alt.group(1)
        except Exception as e:
            logger.debug("Unable to resolve channel ID for %s: %s", handle, e)

    return None


def get_youtube_rss_url(url_or_handle: str) -> Optional[str]:
    """
    Returns native YouTube RSS feed URL if input is a YouTube channel, playlist, or handle.
    """
    target = url_or_handle.strip()

    # Playlist (youtube.com or youtu.be with list param)
    match_playlist = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", target)
    if ("youtube.com" in target.lower() or "youtu.be" in target.lower()) and match_playlist:
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={match_playlist.group(1)}"

    # Channel ID or Handle
    channel_id = extract_youtube_channel_id(target)
    if channel_id:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    return None

