import os
import sys
import time
import tempfile
import unittest
from pathlib import Path

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.datehandler import DateHandler
from utils.database import DatabaseHandler


class TestDatabaseAndDate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.temp_dir.name) / "test.db"
        self.db = DatabaseHandler(str(self.db_file))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_date_handler_struct_time(self):
        st = time.struct_time((2026, 8, 18, 12, 0, 0, 1, 230, 0))
        dt = DateHandler.parse_datetime(st)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 8)
        self.assertEqual(dt.day, 18)

    def test_add_bookmark_auto_creates_user(self):
        # Adding a bookmark for a non-existing user should not fail with foreign key error
        user_id = 999888
        self.db.add_user_bookmark(
            telegram_id=user_id,
            url="https://duccio.me/rss",
            alias="Duccio",
            telegraph=True,
        )
        bookmarks = self.db.get_urls_for_user(user_id)
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0][0], "https://duccio.me/rss")
        self.assertEqual(bookmarks[0][1], "Duccio")
        self.assertEqual(bookmarks[0][5], 1)  # telegraph = True

    def test_update_filter_rules(self):
        user_id = 12345
        self.db.add_user_bookmark(
            telegram_id=user_id,
            url="https://duccio.me/rss",
            alias="🔥 Tech News",
            telegraph=False,
        )
        success = self.db.update_user_bookmark_filter(user_id, "🔥 Tech News", "+python -crypto")
        self.assertTrue(success)
        bookmarks = self.db.get_urls_for_user(user_id)
        self.assertEqual(bookmarks[0][4], "+python -crypto")

    def test_legacy_database_auto_migration(self):
        # Create a legacy SQLite database without last_entry_id and filter_rules
        legacy_file = Path(self.temp_dir.name) / "legacy.db"
        import sqlite3
        conn = sqlite3.connect(str(legacy_file))
        conn.executescript("""
            CREATE TABLE user (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                firstname TEXT NOT NULL,
                lastname TEXT,
                language TEXT,
                is_bot INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE web (
                url TEXT PRIMARY KEY,
                last_title TEXT NOT NULL,
                last_updated TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE web_user (
                url TEXT,
                telegram_id INTEGER,
                alias TEXT NOT NULL,
                telegraph INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (url, telegram_id)
            );
            INSERT INTO user (telegram_id, firstname, is_active) VALUES (1, 'Test', 1);
            INSERT INTO web (url, last_title, last_updated) VALUES ('https://duccio.me/rss', 'Old Title', '1999-01-01');
            INSERT INTO web_user (url, telegram_id, alias) VALUES ('https://duccio.me/rss', 1, 'My Blog');
        """)
        conn.close()

        # Opening with DatabaseHandler should auto-migrate without error
        legacy_db = DatabaseHandler(str(legacy_file))
        feeds = legacy_db.get_all_feeds()
        self.assertEqual(len(feeds), 1)
        self.assertEqual(feeds[0][0], "https://duccio.me/rss")
        self.assertIsNone(feeds[0][3])  # last_entry_id migrated as NULL

        # Test updating the feed with last_entry_id
        legacy_db.update_feed("https://duccio.me/rss", "2026-08-18", "New Title", "guid-123")
        feeds_updated = legacy_db.get_all_feeds()
        self.assertEqual(feeds_updated[0][3], "guid-123")


if __name__ == "__main__":
    unittest.main()
