import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock third-party dependencies if not installed in current environment
for mod_name in ["feedparser", "bs4", "requests", "telegram", "telegram.ext", "telegram.error", "dotenv", "html_telegraph_poster", "webpage2telegraph", "trafilatura"]:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            sys.modules[mod_name] = MagicMock()

# Add src to pythonpath
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from providers.models import FeedItem
from providers.base import BaseFeedProvider
from providers.local_rss import LocalRSSProvider
from providers.lion_reader import LionReaderProvider
from providers import get_feed_provider


class TestProviders(unittest.TestCase):
    def test_feed_item_model(self):
        item = FeedItem(
            id="123",
            title="Test Title",
            link="https://example.com/post",
            summary="Summary text",
            source_link="https://example.com/source",
        )
        self.assertEqual(item.id, "123")
        self.assertEqual(item.title, "Test Title")
        self.assertEqual(item.link, "https://example.com/post")
        self.assertEqual(item.source_link, "https://example.com/source")

    def test_local_rss_provider_factory(self):
        provider = get_feed_provider("local")
        self.assertIsInstance(provider, LocalRSSProvider)
        self.assertIsInstance(provider, BaseFeedProvider)

    def test_lion_reader_provider_factory(self):
        provider = get_feed_provider("lion_reader", api_url="http://test-lion.local", api_key="secret123")
        self.assertIsInstance(provider, LionReaderProvider)
        self.assertEqual(provider.base_url, "http://test-lion.local")
        self.assertEqual(provider.api_token, "secret123")

    def test_lion_reader_headers(self):
        provider = LionReaderProvider(base_url="http://localhost:3000", api_token="my-token")
        headers = provider._get_headers()
        self.assertEqual(headers["Authorization"], "Bearer my-token")
        self.assertEqual(headers["Accept"], "application/json")

    @patch("providers.lion_reader.requests.get")
    def test_lion_reader_fetch_entries(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entries": [
                {
                    "id": "entry-1",
                    "title": "Lion Article 1",
                    "url": "https://example.com/lion1",
                    "publishedAt": "2026-08-18T10:00:00Z",
                    "summary": "Sample summary",
                },
                {
                    "id": "entry-2",
                    "title": "Lion Article 2",
                    "url": "https://example.com/lion2",
                },
            ]
        }
        mock_get.return_value = mock_response

        provider = LionReaderProvider(base_url="http://localhost:3000")
        items = provider.fetch_entries("https://example.com/feed.xml", limit=10)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].id, "entry-1")
        self.assertEqual(items[0].title, "Lion Article 1")
        self.assertEqual(items[0].link, "https://example.com/lion1")
        self.assertEqual(items[1].id, "entry-2")

    @patch("utils.feedhandler.FeedHandler.parse_N_entries")
    @patch("utils.feedhandler.FeedHandler.get_entry_id")
    def test_local_rss_fetch_entries(self, mock_entry_id, mock_parse_n):
        mock_entry = MagicMock()
        mock_entry.title = "Local RSS Article"
        mock_entry.link = "https://example.com/rss1"
        mock_entry.published = "2026-08-18"
        mock_entry.summary = "Local summary"
        mock_parse_n.return_value = [mock_entry]
        mock_entry_id.return_value = "guid-local-1"

        provider = LocalRSSProvider()
        items = provider.fetch_entries("https://example.com/feed.xml", limit=1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "guid-local-1")
        self.assertEqual(items[0].title, "Local RSS Article")
        self.assertEqual(items[0].link, "https://example.com/rss1")


if __name__ == "__main__":
    unittest.main()
