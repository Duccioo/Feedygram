import sys
import unittest
from pathlib import Path

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.reddit import extract_reddit_target


class TestReddit(unittest.TestCase):
    def test_subreddit_shorthand(self):
        self.assertEqual(extract_reddit_target("r/technology"), "https://www.reddit.com/r/technology/.rss")
        self.assertEqual(extract_reddit_target("/r/python/"), "https://www.reddit.com/r/python/.rss")

    def test_user_shorthand(self):
        self.assertEqual(extract_reddit_target("u/spez"), "https://www.reddit.com/user/spez/.rss")
        self.assertEqual(extract_reddit_target("user/spez"), "https://www.reddit.com/user/spez/.rss")

    def test_full_url(self):
        self.assertEqual(extract_reddit_target("https://www.reddit.com/r/programming/"), "https://www.reddit.com/r/programming/.rss")
        self.assertEqual(extract_reddit_target("http://reddit.com/user/someone"), "https://www.reddit.com/user/someone/.rss")

    def test_non_reddit_url(self):
        self.assertIsNone(extract_reddit_target("https://duccio.me/rss"))


if __name__ == "__main__":
    unittest.main()
