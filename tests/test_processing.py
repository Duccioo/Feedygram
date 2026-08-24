import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

for mod_name in [
    "telegram",
    "telegram.ext",
    "telegram.error",
    "feedparser",
    "bs4",
    "requests",
    "dotenv",
    "html_telegraph_poster",
    "webpage2telegraph",
    "trafilatura",
]:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            sys.modules[mod_name] = MagicMock()

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from providers.models import FeedItem
from command.processing import BatchProcess


class TestProcessing(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_bot = MagicMock()
        self.mock_provider = MagicMock()
        self.processor = BatchProcess(
            database=self.mock_db,
            update_interval=60,
            bot=self.mock_bot,
            provider=self.mock_provider,
        )

    def test_filter_new_entries_first_run(self):
        """When last_entry_id is None, all available entries must be returned"""
        items = [
            FeedItem(id="item-1", title="Item 1", link="https://example.com/1"),
            FeedItem(id="item-2", title="Item 2", link="https://example.com/2"),
            FeedItem(id="item-3", title="Item 3", link="https://example.com/3"),
        ]
        result = self.processor._filter_new_entries(items, last_entry_id=None)
        self.assertEqual(len(result), 3)
        self.assertEqual([e.id for e in result], ["item-1", "item-2", "item-3"])

    def test_filter_new_entries_empty_string_id(self):
        """When last_entry_id is empty string, all entries must be returned"""
        items = [
            FeedItem(id="item-1", title="Item 1", link="https://example.com/1"),
            FeedItem(id="item-2", title="Item 2", link="https://example.com/2"),
        ]
        result = self.processor._filter_new_entries(items, last_entry_id="")
        self.assertEqual(len(result), 2)

    def test_filter_new_entries_subsequent_run(self):
        """When last_entry_id is found, only newer entries (before it) are returned"""
        items = [
            FeedItem(id="item-3", title="Item 3", link="https://example.com/3"),
            FeedItem(id="item-2", title="Item 2", link="https://example.com/2"),
            FeedItem(id="item-1", title="Item 1", link="https://example.com/1"),
        ]
        # item-2 was the last processed entry
        result = self.processor._filter_new_entries(items, last_entry_id="item-2")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "item-3")

    def test_filter_new_entries_no_new_articles(self):
        """When the newest entry matches last_entry_id, empty list returned"""
        items = [
            FeedItem(id="item-3", title="Item 3", link="https://example.com/3"),
            FeedItem(id="item-2", title="Item 2", link="https://example.com/2"),
        ]
        result = self.processor._filter_new_entries(items, last_entry_id="item-3")
        self.assertEqual(len(result), 0)

    def test_filter_new_entries_not_found_in_window(self):
        """When last_entry_id is old and rotated out, return all available entries"""
        items = [
            FeedItem(id="item-5", title="Item 5", link="https://example.com/5"),
            FeedItem(id="item-4", title="Item 4", link="https://example.com/4"),
        ]
        result = self.processor._filter_new_entries(items, last_entry_id="item-1")
        self.assertEqual(len(result), 2)
        self.assertEqual([e.id for e in result], ["item-5", "item-4"])

    def test_filter_new_entries_empty_list(self):
        """Empty entries list should return empty list"""
        result = self.processor._filter_new_entries([], last_entry_id="item-1")
        self.assertEqual(result, [])

    def test_filter_new_entries_with_known_ids_set(self):
        """Articles matching any ID in the 50-item known_ids set should be skipped"""
        items = [
            FeedItem(id="item-3", title="Item 3", link="https://example.com/3"),
            FeedItem(id="item-2", title="Item 2", link="https://example.com/2"),
            FeedItem(id="item-1", title="Item 1", link="https://example.com/1"),
        ]
        known_ids = {"item-2", "item-1", "item-0"}
        result = self.processor._filter_new_entries(items, known_entry_ids=known_ids)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "item-3")

    def test_process_single_feed_new_subscription(self):
        """On new subscription (last_entry_id is None), all entries are notified and latest is saved"""
        import asyncio

        items = [
            FeedItem(id="item-new", title="Newest", link="https://example.com/new"),
            FeedItem(id="item-old", title="Oldest", link="https://example.com/old"),
        ]
        self.mock_provider.fetch_entries.return_value = items
        self.mock_db.get_active_users_for_feed.return_value = [
            (12345, False, "TestFeed", "")
        ]

        async def _test():
            await self.processor._process_single_feed(
                feed_url="https://example.com/rss",
                last_updated=None,
                last_title="",
                last_entry_id=None,
            )

        asyncio.run(_test())

        # Check that update_feed was called with latest entry ID
        self.mock_db.update_feed.assert_called_once_with(
            url="https://example.com/rss",
            last_updated=None,
            last_title="Newest",
            last_entry_id="item-new",
        )


if __name__ == "__main__":
    unittest.main()
