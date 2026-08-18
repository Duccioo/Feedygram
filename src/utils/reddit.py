import re
from typing import Optional


def extract_reddit_target(target: str) -> Optional[str]:
    """
    Detects if input is a subreddit or Reddit user profile and returns native RSS URL.
    Supported formats:
    - 'r/technology' or '/r/technology'
    - 'u/spez' or 'user/spez'
    - 'https://reddit.com/r/technology'
    - 'https://www.reddit.com/user/spez'
    """
    target = target.strip()

    # Subreddit shorthand: r/subreddit or /r/subreddit
    match_r = re.match(r"^/?r/([A-Za-z0-9_]{2,30})/?$", target, re.IGNORECASE)
    if match_r:
        return f"https://www.reddit.com/r/{match_r.group(1)}/.rss"

    # User shorthand: u/username or user/username
    match_u = re.match(r"^/?(?:u|user)/([A-Za-z0-9_-]{2,30})/?$", target, re.IGNORECASE)
    if match_u:
        return f"https://www.reddit.com/user/{match_u.group(1)}/.rss"

    # Full Reddit URL
    match_url_r = re.search(r"reddit\.com/r/([A-Za-z0-9_]{2,30})", target, re.IGNORECASE)
    if match_url_r:
        return f"https://www.reddit.com/r/{match_url_r.group(1)}/.rss"

    match_url_u = re.search(r"reddit\.com/user/([A-Za-z0-9_-]{2,30})", target, re.IGNORECASE)
    if match_url_u:
        return f"https://www.reddit.com/user/{match_url_u.group(1)}/.rss"

    return None

