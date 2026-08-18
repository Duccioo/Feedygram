import os
import sys
import unittest
from pathlib import Path

# Add src to pythonpath
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.twitter import (
    extract_twitter_username,
    get_twitter_rss_url,
    get_candidate_twitter_rss_urls,
    convert_to_fxtwitter_url,
)


class TestTwitterResolver(unittest.TestCase):
    def test_extract_username(self):
        self.assertEqual(extract_twitter_username("@elonmusk"), "elonmusk")
        self.assertEqual(extract_twitter_username("https://x.com/elonmusk"), "elonmusk")
        self.assertEqual(extract_twitter_username("http://twitter.com/OpenAI/"), "OpenAI")
        self.assertEqual(extract_twitter_username("x.com/sama?s=20"), "sama")
        self.assertIsNone(extract_twitter_username("https://duccio.me/rss"))
        self.assertIsNone(extract_twitter_username("https://x.com/home"))
        self.assertIsNone(extract_twitter_username("https://x.com/elonmusk/status/123456789"))

    def test_get_twitter_rss_url_default(self):
        url = get_twitter_rss_url("elonmusk")
        self.assertIn("elonmusk", url)
        self.assertTrue(url.startswith("http"))

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


if __name__ == "__main__":
    unittest.main()
