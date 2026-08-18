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


if __name__ == "__main__":
    unittest.main()
