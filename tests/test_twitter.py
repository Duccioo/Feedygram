import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to pythonpath
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.twitter import (
    extract_twitter_username,
    get_twitter_rss_url,
    get_candidate_twitter_rss_urls,
    convert_to_fxtwitter_url,
    fetch_twitter_syndication_entries,
    validate_twitter_user,
    get_twitter_user_title,
)


class TestTwitterResolver(unittest.TestCase):
    def test_extract_username(self):
        self.assertEqual(extract_twitter_username("@elonmusk"), "elonmusk")
        self.assertEqual(extract_twitter_username("https://x.com/elonmusk"), "elonmusk")
        self.assertEqual(extract_twitter_username("http://twitter.com/OpenAI/"), "OpenAI")
        self.assertEqual(extract_twitter_username("x.com/sama?s=20"), "sama")
        self.assertEqual(extract_twitter_username("https://nitter.net/ericmigi/rss"), "ericmigi")
        self.assertEqual(extract_twitter_username("https://xcancel.com/ericmigi/rss"), "ericmigi")
        self.assertEqual(extract_twitter_username("https://openrss.org/twitter.com/ericmigi"), "ericmigi")
        self.assertEqual(
            extract_twitter_username("https://syndication.twitter.com/srv/timeline-profile/screen-name/ericmigi"),
            "ericmigi",
        )
        self.assertIsNone(extract_twitter_username("https://duccio.me/rss"))
        self.assertIsNone(extract_twitter_username("https://x.com/home"))
        self.assertIsNone(extract_twitter_username("https://x.com/elonmusk/status/123456789"))

    def test_get_twitter_rss_url_default(self):
        url = get_twitter_rss_url("elonmusk")
        self.assertEqual(url, "https://x.com/elonmusk")

    def test_get_twitter_rss_url_custom_env(self):
        os.environ["TWITTER_RSS_BRIDGE"] = "https://custom-bridge.org/{username}/rss"
        try:
            url = get_twitter_rss_url("elonmusk")
            self.assertEqual(url, "https://custom-bridge.org/elonmusk/rss")
        finally:
            del os.environ["TWITTER_RSS_BRIDGE"]

    def test_candidate_urls(self):
        candidates = get_candidate_twitter_rss_urls("naval")
        self.assertTrue(len(candidates) >= 2)
        for cand in candidates:
            self.assertIn("naval", cand)

    def test_convert_to_fxtwitter_url(self):
        self.assertEqual(
            convert_to_fxtwitter_url("https://twitter.com/karpathy/status/1234567890"),
            "https://fxtwitter.com/karpathy/status/1234567890",
        )
        self.assertEqual(
            convert_to_fxtwitter_url("https://x.com/karpathy/status/1234567890"),
            "https://fxtwitter.com/karpathy/status/1234567890",
        )
        self.assertEqual(
            convert_to_fxtwitter_url("https://nitter.net/karpathy/status/1234567890"),
            "https://fxtwitter.com/karpathy/status/1234567890",
        )
        self.assertEqual(
            convert_to_fxtwitter_url("https://duccio.me/my-article"),
            "https://duccio.me/my-article",
        )

    @patch("utils.twitter.requests.get")
    def test_fetch_twitter_syndication_entries(self, mock_get):
        mock_html = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "timeline": {
                        "entries": [
                            {
                                "content": {
                                    "tweet": {
                                        "id_str": "123456789",
                                        "text": "Hello world from Twitter https://t.co/xyz #tech",
                                        "created_at": "Mon Jan 27 20:07:59 +0000 2025",
                                        "user": {
                                            "name": "Eric M",
                                            "screen_name": "ericmigi"
                                        },
                                        "entities": {
                                            "urls": [{"url": "https://t.co/xyz", "expanded_url": "https://pebble.com"}],
                                            "hashtags": [{"text": "tech"}]
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        </script>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html
        mock_get.return_value = mock_resp

        items = fetch_twitter_syndication_entries("@ericmigi", limit=5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "123456789")
        self.assertIn("https://pebble.com", items[0].title)
        self.assertEqual(items[0].link, "https://x.com/ericmigi/status/123456789")
        self.assertEqual(items[0].source_link, "https://fxtwitter.com/ericmigi/status/123456789")
        self.assertEqual(items[0].tags, ["tech"])

    @patch("utils.twitter.requests.get")
    def test_validate_twitter_user(self, mock_get):
        mock_html_ok = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "contextProvider": {"hasResults": true},
                    "timeline": {"entries": [{"content": {"tweet": {"id_str": "1"}}}]}
                }
            }
        }
        </script>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html_ok
        mock_get.return_value = mock_resp

        is_ok, err = validate_twitter_user("@ericmigi")
        self.assertTrue(is_ok)
        self.assertIsNone(err)

    @patch("utils.twitter.requests.get")
    def test_validate_twitter_user_nonexistent(self, mock_get):
        mock_html_empty = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "contextProvider": {"hasResults": false},
                    "timeline": {"entries": []}
                }
            }
        }
        </script>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html_empty
        mock_get.return_value = mock_resp

        is_ok, err = validate_twitter_user("@fakeuser")
        self.assertFalse(is_ok)
        self.assertIsNotNone(err)


if __name__ == "__main__":
    unittest.main()

