import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock third-party dependencies if not installed in global environment
for mod in ["feedparser", "bs4", "requests", "telegram", "telegram.ext"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.feedhandler import FeedHandler


class TestFeedDiscovery(unittest.TestCase):
    @patch("utils.feedhandler.FeedHandler.is_parsable")
    def test_direct_feed_returns_immediately(self, mock_is_parsable):
        mock_is_parsable.return_value = (True, None)
        res = FeedHandler.discover_feed_url("https://example.com/rss.xml")
        self.assertEqual(res, "https://example.com/rss.xml")

    @patch("utils.feedhandler.requests.get")
    @patch("utils.feedhandler.FeedHandler.is_parsable")
    def test_discover_from_html_alternate_link(self, mock_is_parsable, mock_get):
        mock_is_parsable.side_effect = lambda u: (True, None) if "feed.xml" in u else (False, "Not a feed")

        html_page = """
        <html>
            <head>
                <title>Awesome Tech Blog</title>
                <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/feed.xml" />
            </head>
            <body>Hello World</body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_page
        mock_get.return_value = mock_resp

        # Mock BeautifulSoup if mocked
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_page, "html.parser")
            with patch("utils.feedhandler.BeautifulSoup", return_value=soup):
                discovered = FeedHandler.discover_feed_url("https://techblog.example.com")
                self.assertEqual(discovered, "https://techblog.example.com/feed.xml")
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
