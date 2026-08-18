import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.youtube import extract_youtube_channel_id, get_youtube_rss_url


class TestYouTube(unittest.TestCase):
    def test_direct_channel_id(self):
        cid = "UCBJycsmduvYEL83R_U4JriQ"
        url = get_youtube_rss_url(cid)
        self.assertEqual(url, f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")

    def test_channel_url(self):
        url = "https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ"
        rss = get_youtube_rss_url(url)
        self.assertEqual(rss, "https://www.youtube.com/feeds/videos.xml?channel_id=UCBJycsmduvYEL83R_U4JriQ")

    def test_playlist_url(self):
        url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOdP_8GzKtO4GdiGl50POUEd"
        rss = get_youtube_rss_url(url)
        self.assertEqual(rss, "https://www.youtube.com/feeds/videos.xml?playlist_id=PLrAXtmErZgOdP_8GzKtO4GdiGl50POUEd")

    def test_youtu_be_playlist(self):
        url = "https://youtu.be/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOdP_8GzKtO4GdiGl50POUEd"
        rss = get_youtube_rss_url(url)
        self.assertEqual(rss, "https://www.youtube.com/feeds/videos.xml?playlist_id=PLrAXtmErZgOdP_8GzKtO4GdiGl50POUEd")

    def test_non_youtube_url(self):
        self.assertIsNone(get_youtube_rss_url("https://duccio.me/rss"))


if __name__ == "__main__":
    unittest.main()
