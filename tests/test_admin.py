import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock third-party dependencies if not installed
for mod in ["telegram", "telegram.ext", "requests", "feedparser", "bs4", "html_telegraph_poster", "webpage2telegraph", "trafilatura"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.database import DatabaseHandler
from command.admin import (
    is_admin,
    get_max_feeds_limit,
    set_max_feeds_limit,
    make_admin_dashboard_keyboard,
    make_max_feeds_keyboard,
    make_broadcast_confirm_keyboard,
    make_back_to_admin_keyboard,
    format_admin_dashboard_message,
    format_system_stats_message,
)


class TestAdmin(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_admin.db"
        self.db = DatabaseHandler(str(self.db_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_admin(self):
        with patch.dict(os.environ, {"ADMIN_USER_ID": "12345678, 87654321"}):
            self.assertTrue(is_admin(12345678))
            self.assertTrue(is_admin("12345678"))
            self.assertTrue(is_admin(87654321))
            self.assertFalse(is_admin(99999999))
            self.assertFalse(is_admin(""))
            self.assertFalse(is_admin(None))

        with patch.dict(os.environ, {"ADMIN_ID": "55555", "ADMIN_USER_ID": ""}):
            self.assertTrue(is_admin(55555))
            self.assertFalse(is_admin(12345))

        with patch.dict(os.environ, {"ADMIN_ID": "", "ADMIN_USER_ID": ""}):
            self.assertFalse(is_admin(12345678))

    def test_max_feeds_limit_default_and_env(self):
        with patch.dict(os.environ, {"MAX_FEEDS_PER_USER": "20"}):
            # No setting in DB yet, should read from env
            self.assertEqual(get_max_feeds_limit(self.db), 20)

        with patch.dict(os.environ, {"MAX_FEEDS_PER_USER": ""}):
            # Fallback to default (15)
            self.assertEqual(get_max_feeds_limit(self.db), 15)

    def test_max_feeds_limit_db_persistence(self):
        # Setting via database overrides env
        with patch.dict(os.environ, {"MAX_FEEDS_PER_USER": "10"}):
            set_max_feeds_limit(self.db, 35)
            self.assertEqual(get_max_feeds_limit(self.db), 35)

            # Setting to 0 (unlimited)
            set_max_feeds_limit(self.db, 0)
            self.assertEqual(get_max_feeds_limit(self.db), 0)

    def test_keyboards_structure(self):
        dash_kb = make_admin_dashboard_keyboard()
        self.assertIsNotNone(dash_kb)

        max_kb = make_max_feeds_keyboard(current_limit=15)
        self.assertIsNotNone(max_kb)

        bc_kb = make_broadcast_confirm_keyboard()
        self.assertIsNotNone(bc_kb)

        back_kb = make_back_to_admin_keyboard()
        self.assertIsNotNone(back_kb)

    def test_message_formatters(self):
        mock_user = MagicMock()
        mock_user.first_name = "Mario"
        stats = {
            "total_users": 10,
            "active_users": 8,
            "total_feeds": 5,
            "active_feeds": 4,
            "total_subscriptions": 12,
            "total_history": 50,
            "db_size_bytes": 10240,
        }

        dash_msg = format_admin_dashboard_message(stats, current_limit=15, admin_user=mock_user)
        self.assertIn("Mario", dash_msg)
        self.assertIn("15", dash_msg)
        self.assertIn("8", dash_msg)

        diag_msg = format_system_stats_message(stats, provider_name="LocalRSSProvider", interval=300)
        self.assertIn("LocalRSSProvider", diag_msg)
        self.assertIn("300s", diag_msg)
        self.assertIn("10.0 KB", diag_msg)

    def test_database_admin_methods(self):
        # 1. Add active and inactive users
        self.db.add_user(1001, "active1", "One", None, "it", False, is_active=True)
        self.db.add_user(1002, "active2", "Two", None, "it", False, is_active=True)
        self.db.add_user(1003, "inactive", "Three", None, "it", False, is_active=False)

        active_ids = self.db.get_all_active_user_ids()
        self.assertEqual(active_ids, [1001, 1002])

        # 2. Add feeds and bookmarks
        self.db.add_user_bookmark(1001, "https://example.com/rss1", "Feed 1", False)
        self.db.add_url("https://example.com/orphaned")

        stats = self.db.get_system_stats()
        self.assertEqual(stats["total_users"], 3)
        self.assertEqual(stats["active_users"], 2)
        self.assertEqual(stats["total_feeds"], 2)
        self.assertEqual(stats["active_feeds"], 1)

        # 3. Prune orphaned feeds
        pruned = self.db.prune_orphaned_feeds()
        self.assertEqual(pruned, 1)

        stats_after = self.db.get_system_stats()
        self.assertEqual(stats_after["total_feeds"], 1)

    def test_feed_limit_logic(self):
        with patch.dict(os.environ, {"ADMIN_USER_ID": "9999"}):
            admin_id = 9999
            user_id = 1111

            set_max_feeds_limit(self.db, 2)
            limit = get_max_feeds_limit(self.db)
            self.assertEqual(limit, 2)

            # User adds 2 bookmarks
            self.db.add_user_bookmark(user_id, "https://example.com/feed1", "F1", False)
            self.db.add_user_bookmark(user_id, "https://example.com/feed2", "F2", False)
            user_feeds = self.db.get_urls_for_user(user_id)
            self.assertEqual(len(user_feeds), 2)

            # Check if user reached limit
            self.assertTrue(limit > 0 and not is_admin(user_id) and len(user_feeds) >= limit)

            # Admin adds 3 bookmarks (exceeds limit without restriction)
            self.db.add_user_bookmark(admin_id, "https://example.com/a1", "A1", False)
            self.db.add_user_bookmark(admin_id, "https://example.com/a2", "A2", False)
            self.db.add_user_bookmark(admin_id, "https://example.com/a3", "A3", False)
            admin_feeds = self.db.get_urls_for_user(admin_id)
            self.assertEqual(len(admin_feeds), 3)

            # Admin is exempt from limit check
            self.assertFalse(limit > 0 and not is_admin(admin_id) and len(admin_feeds) >= limit)


if __name__ == "__main__":
    unittest.main()
