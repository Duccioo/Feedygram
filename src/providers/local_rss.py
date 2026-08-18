from typing import List, Tuple, Optional
from utils.feedhandler import FeedHandler
from utils.datehandler import DateHandler
from .base import BaseFeedProvider
from .models import FeedItem


class LocalRSSProvider(BaseFeedProvider):
    """
    Provider predefinito basato su feedparser locale.
    """

    def validate_feed(self, target: str) -> Tuple[bool, Optional[str]]:
        return FeedHandler.is_parsable(target)

    def get_feed_title(self, target: str) -> Optional[str]:
        return FeedHandler.get_feed_title(target)

    def fetch_entries(self, target: str, limit: int = 0) -> List[FeedItem]:
        raw_entries = FeedHandler.parse_N_entries(target, limit)
        if not raw_entries:
            return []

        items: List[FeedItem] = []
        for entry in raw_entries:
            entry_id = FeedHandler.get_entry_id(entry)
            title = getattr(entry, "title", "No Title")
            link = getattr(entry, "link", "")
            source_link = FeedHandler.extract_source_link(entry)

            date_val = getattr(entry, "published", None) or getattr(entry, "updated", None)
            parsed_date = DateHandler.parse_datetime(date_val) if date_val else None

            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

            # Estrazione categorie / tag nativi dal feed
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
