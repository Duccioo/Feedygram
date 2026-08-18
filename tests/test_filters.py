import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

for mod in ["feedparser", "requests", "bs4"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from providers.models import FeedItem
from utils.filters import matches_filter


class TestFilters(unittest.TestCase):
    def test_no_filter_rules(self):
        item = FeedItem(id="1", title="Python 3.12 released", link="https://example.com/1")
        self.assertTrue(matches_filter(item, ""))
        self.assertTrue(matches_filter(item, "   "))

    def test_positive_filter_match(self):
        item = FeedItem(id="1", title="Learning Python and Machine Learning", link="https://example.com/1")
        self.assertTrue(matches_filter(item, "+python"))
        self.assertTrue(matches_filter(item, "python"))

    def test_positive_filter_mismatch(self):
        item = FeedItem(id="1", title="JavaScript updates for 2026", link="https://example.com/1")
        self.assertFalse(matches_filter(item, "+python"))

    def test_negative_filter_exclude(self):
        item = FeedItem(id="1", title="Crypto market soars with Bitcoin", link="https://example.com/1")
        self.assertFalse(matches_filter(item, "-crypto"))

    def test_combined_filter(self):
        item1 = FeedItem(id="1", title="Python in Web3 and Crypto", link="https://example.com/1")
        item2 = FeedItem(id="2", title="Python Fast APIs and Web development", link="https://example.com/2")
        item3 = FeedItem(id="3", title="Rust for Web development", link="https://example.com/3")

        rules = "+python -crypto -web3"
        self.assertFalse(matches_filter(item1, rules))  # Has python but also crypto/web3 -> False
        self.assertTrue(matches_filter(item2, rules))   # Has python and no crypto -> True
        self.assertFalse(matches_filter(item3, rules))  # No python -> False

    def test_filter_with_tags(self):
        item = FeedItem(id="4", title="New AI model release", link="https://example.com/4", tags=["Python", "Deep Learning"])
        self.assertTrue(matches_filter(item, "+python"))
        self.assertFalse(matches_filter(item, "+javascript"))


if __name__ == "__main__":
    unittest.main()
