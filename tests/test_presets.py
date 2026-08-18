import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

for mod in ["telegram", "telegram.ext", "requests", "feedparser", "bs4"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.presets import PRESETS_DATA, make_categories_keyboard, make_category_feeds_keyboard


class TestPresets(unittest.TestCase):
    def test_presets_structure(self):
        self.assertIn("💻 Tech & Dev", PRESETS_DATA)
        self.assertIn("🌍 News & World", PRESETS_DATA)
        tech_feeds = PRESETS_DATA["💻 Tech & Dev"]
        self.assertTrue(len(tech_feeds) >= 2)
        for f in tech_feeds:
            self.assertIn("name", f)
            self.assertIn("url", f)
            self.assertTrue(f["url"].startswith("http"))

    def test_make_categories_keyboard(self):
        kb = make_categories_keyboard()
        self.assertIsNotNone(kb)

    def test_make_category_feeds_keyboard(self):
        msg, kb = make_category_feeds_keyboard("💻 Tech & Dev")
        self.assertIn("Tech", msg)
        self.assertIsNotNone(kb)

    def test_unknown_category(self):
        msg, kb = make_category_feeds_keyboard("Unknown Category")
        self.assertIn("No feeds found", msg)



if __name__ == "__main__":
    unittest.main()
