from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from .models import FeedItem


class BaseFeedProvider(ABC):
    """
    Common interface for RSS/Atom feed providers or external feed engines (e.g. Lion Reader, REST API).
    """

    @abstractmethod
    def validate_feed(self, target: str) -> Tuple[bool, Optional[str]]:
        """Verifies if feed URL or identifier is valid and reachable."""
        pass

    @abstractmethod
    def get_feed_title(self, target: str) -> Optional[str]:
        """Retrieves the feed title."""
        pass

    @abstractmethod
    def fetch_entries(self, target: str, limit: int = 0) -> List[FeedItem]:
        """Fetches feed entries for the specified target."""
        pass

