import os
from typing import Optional
from .models import FeedItem
from .base import BaseFeedProvider
from .local_rss import LocalRSSProvider
from .lion_reader import LionReaderProvider


def get_feed_provider(
    provider_name: Optional[str] = None,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseFeedProvider:
    """
    Factory per ottenere l'istanza del provider di feed configurato.
    """
    provider_type = (provider_name or os.environ.get("FEED_PROVIDER", "local")).lower().strip()

    if provider_type in ("lion_reader", "lion", "api", "rest"):
        url = api_url or os.environ.get("FEED_API_URL", "http://localhost:3000")
        key = api_key or os.environ.get("FEED_API_KEY")
        return LionReaderProvider(base_url=url, api_token=key)

    # Predefinito: LocalRSSProvider
    return LocalRSSProvider()


__all__ = [
    "FeedItem",
    "BaseFeedProvider",
    "LocalRSSProvider",
    "LionReaderProvider",
    "get_feed_provider",
]
