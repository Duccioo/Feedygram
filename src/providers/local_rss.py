from typing import List, Tuple, Optional
from utils.feedhandler import FeedHandler
from utils.datehandler import DateHandler
from utils.twitter import (
    extract_twitter_username,
    fetch_twitter_syndication_entries,
    validate_twitter_user,
    get_twitter_user_title,
    get_candidate_twitter_rss_urls,
)
from .base import BaseFeedProvider
from .models import FeedItem


class LocalRSSProvider(BaseFeedProvider):
    """
    Default provider based on local feedparser with native Twitter / X resolver and automatic bridge fallbacks.
    """

    def validate_feed(self, target: str) -> Tuple[bool, Optional[str]]:
        twitter_user = extract_twitter_username(target)
        if twitter_user:
            is_ok, err = validate_twitter_user(twitter_user)
            if is_ok:
                return True, None
            # Automatic fallback: test candidate RSS bridges
            for candidate in get_candidate_twitter_rss_urls(twitter_user):
                if "x.com" in candidate or "twitter.com" in candidate:
                    continue
                is_rss_ok, _ = FeedHandler.is_parsable(candidate)
                if is_rss_ok:
                    return True, None
            return False, err

        return FeedHandler.is_parsable(target)

    def get_feed_title(self, target: str) -> Optional[str]:
        twitter_user = extract_twitter_username(target)
        if twitter_user:
            tw_title = get_twitter_user_title(twitter_user)
            if tw_title:
                return tw_title
            for candidate in get_candidate_twitter_rss_urls(twitter_user):
                if "x.com" in candidate or "twitter.com" in candidate:
                    continue
                cand_title = FeedHandler.get_feed_title(candidate)
                if cand_title:
                    return cand_title

        return FeedHandler.get_feed_title(target)

    def fetch_entries(self, target: str, limit: int = 0) -> List[FeedItem]:
        raw_entries = None
        twitter_user = extract_twitter_username(target)
        if twitter_user:
            tw_items = fetch_twitter_syndication_entries(twitter_user, limit=limit)
            if tw_items:
                return tw_items

            # Automatic fallback: try candidate RSS bridges if syndication fails
            for candidate in get_candidate_twitter_rss_urls(twitter_user):
                if "x.com" in candidate or "twitter.com" in candidate:
                    continue
                candidate_entries = FeedHandler.parse_N_entries(candidate, limit)
                if candidate_entries:
                    raw_entries = candidate_entries
                    break
        else:
            raw_entries = FeedHandler.parse_N_entries(target, limit)

        if not raw_entries:
            return []

        items: List[FeedItem] = []
        for entry in raw_entries:
            entry_id = FeedHandler.get_entry_id(entry)
            title = getattr(entry, "title", None)
            link = getattr(entry, "link", "")
            source_link = FeedHandler.extract_source_link(entry)

            date_val = getattr(entry, "published", None) or getattr(entry, "updated", None)
            parsed_date = DateHandler.parse_datetime(date_val) if date_val else None

            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            if not title or str(title).strip() in ("", "No Title"):
                if summary:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(summary, "html.parser")
                    clean_summary = " ".join(soup.get_text().split())
                    title = clean_summary if clean_summary else "No Title"
                else:
                    title = "No Title"
            else:
                title = str(title).strip()

            # Extraction of native categories / tags from feed
            raw_tags = getattr(entry, "tags", None) or getattr(entry, "categories", None)
            extracted_tags: List[str] = []
            if raw_tags:
                for t in raw_tags:
                    term = t.get("term") or t.get("label") if isinstance(t, dict) else str(t)
                    if term and str(term).strip():
                        extracted_tags.append(str(term).strip())

            items.append(
                FeedItem(
                    id=entry_id,
                    title=title,
                    link=link,
                    published=parsed_date,
                    summary=summary,
                    source_link=source_link or link,
                    tags=extracted_tags,
                )
            )
        return items


