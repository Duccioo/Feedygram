import logging
import requests
from typing import List, Tuple, Optional, Any, Dict
from utils.datehandler import DateHandler
from .base import BaseFeedProvider
from .models import FeedItem

logger = logging.getLogger(__name__)


class LionReaderProvider(BaseFeedProvider):
    """
    Provider to fetch articles and feeds from a Lion Reader instance (or compatible REST API).
    Supports API Key / Bearer Token authentication and automatic JSON response mapping.
    """

    def __init__(self, base_url: str, api_token: Optional[str] = None, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Feedygram/1.0",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def validate_feed(self, target: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if feed exists or is valid in the API.
        """
        try:
            # ponytail: probe entries endpoint first to verify connection and feed presence
            url = f"{self.base_url}/api/v1/entries"
            params = {"feed": target, "limit": 1}
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            
            if resp.status_code == 404:
                # Try generic alternative endpoint
                url = f"{self.base_url}/api/entries"
                resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)

            if resp.status_code == 200:
                return True, None
            return False, f"API error ({resp.status_code}): {resp.text[:100]}"
        except Exception as e:
            return False, f"Unable to reach Lion Reader API: {e}"

    def get_feed_title(self, target: str) -> Optional[str]:
        """
        Retrieves feed title from API.
        """
        try:
            url = f"{self.base_url}/api/v1/feeds"
            resp = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                feeds = data if isinstance(data, list) else data.get("feeds", data.get("items", []))
                for feed in feeds:
                    if isinstance(feed, dict):
                        if feed.get("url") == target or str(feed.get("id")) == str(target):
                            return feed.get("title") or feed.get("name")
        except Exception as e:
            logger.debug(f"Error retrieving feed title from API: {e}")
        return None

    def fetch_entries(self, target: str, limit: int = 0) -> List[FeedItem]:
        """
        Retrieves articles from Lion Reader API.
        """
        try:
            # Try tRPC / v1 endpoint first
            url = f"{self.base_url}/api/v1/entries"
            params: Dict[str, Any] = {"feed": target}
            if limit > 0:
                params["limit"] = limit

            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            if resp.status_code != 200:
                # Fallback generic REST endpoint
                url = f"{self.base_url}/api/entries"
                resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)

            if resp.status_code != 200:
                logger.warning(f"API response error ({resp.status_code}) for {target}")
                return []

            data = resp.json()
            raw_entries = data if isinstance(data, list) else data.get("entries", data.get("items", []))

            items: List[FeedItem] = []
            for item in raw_entries:
                if not isinstance(item, dict):
                    continue
                
                entry_id = str(item.get("id") or item.get("guid") or item.get("url") or item.get("link") or "")
                title = item.get("title") or "No Title"
                link = item.get("url") or item.get("link") or ""
                summary = item.get("summary") or item.get("content") or item.get("description") or ""
                
                date_str = item.get("publishedAt") or item.get("published") or item.get("createdAt") or item.get("date")
                parsed_date = DateHandler.parse_datetime(date_str) if date_str else None

                raw_tags = item.get("tags") or item.get("categories") or []
                extracted_tags = [str(t).strip() for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else []

                items.append(
                    FeedItem(
                        id=entry_id,
                        title=title,
                        link=link,
                        published=parsed_date,
                        summary=summary,
                        source_link=item.get("sourceUrl") or link,
                        tags=extracted_tags,
                    )
                )

            if limit > 0:
                return items[:limit]
            return items

        except Exception as e:
            logger.error(f"Error fetch_entries from Lion Reader API for {target}: {e}")
            return []

