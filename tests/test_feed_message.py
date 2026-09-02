import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

for mod in ["telegram", "telegram.ext", "requests", "feedparser", "bs4", "html_telegraph_poster", "webpage2telegraph", "trafilatura"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from command.feed_message import send_feed
from utils.make_text import clean_feed_text


class TestFeedMessage(unittest.TestCase):
    def test_send_feed_with_tags(self):
        msg, kb = send_feed(
            telegraph=False,
            alias="TechNews",
            post_link="https://example.com/article",
            post_title="New AI Discovery",
            tags=["AI", "Machine Learning", "Tech & Innovation", "Python"],
        )
        self.assertIn("🏷️ #AI #MachineLearning #TechInnovation #Python", msg)
        self.assertIn("[ TechNews ]", msg)
        self.assertIn("New AI Discovery", msg)

    def test_send_feed_without_tags(self):
        msg, kb = send_feed(
            telegraph=False,
            alias="DuccioBlog",
            post_link="https://example.com/article",
            post_title="Hello World",
            tags=[],
        )
        self.assertNotIn("🏷️", msg)
        self.assertIn("Hello World", msg)

    def test_send_feed_telegraph_mode(self):
        msg, kb = send_feed(
            telegraph=True,
            alias="DuccioBlog",
            post_link="https://example.com/article",
            post_title="Hello World",
            tags=["News"],
        )
        self.assertIn("[ DuccioBlog ]", msg)
        self.assertIn("Hello World", msg)

    def test_send_feed_unescapes_html_entities(self):
        # User reported bug: title with &#8216; and &#8217;
        raw_title = "Google’s new AI transcription edits out your &#8216;ums&#8217; and &#8216;ahs&#8217;"
        msg, kb = send_feed(
            telegraph=False,
            alias="The Verge",
            post_link="https://www.theverge.com/tech/985186/google-gemini-3-5-transcribe-audio-ai",
            post_title=raw_title,
        )
        self.assertNotIn("&#8216;", msg)
        self.assertNotIn("&#8217;", msg)
        self.assertNotIn("&amp;#8216;", msg)
        self.assertIn("‘ums’ and ‘ahs’", msg)

    def test_send_feed_with_double_escaped_entities_and_tags(self):
        raw_title = "<b>Breaking:</b> &amp;#8216;Special Report&amp;#8217; &amp; &quot;Quotes&quot;"
        msg, kb = send_feed(
            telegraph=False,
            alias="NewsFeed",
            post_link="https://example.com/post",
            post_title=raw_title,
            tags=["Tech &amp; AI"],
        )
        self.assertNotIn("<b>", msg)
        self.assertNotIn("</b>", msg)
        self.assertIn("Breaking: ‘Special Report’ &amp; &quot;Quotes&quot;", msg)
        self.assertIn("#TechAI", msg)
        self.assertNotIn("#TechampAI", msg)

    def test_clean_feed_text_utility(self):
        self.assertEqual(
            clean_feed_text("Google’s new AI transcription edits out your &#8216;ums&#8217; and &#8216;ahs&#8217;"),
            "Google’s new AI transcription edits out your ‘ums’ and ‘ahs’",
        )
        self.assertEqual(clean_feed_text("&amp;#8216;test&amp;#8217;"), "‘test’")
        self.assertEqual(clean_feed_text("AT&amp;T"), "AT&T")
        self.assertEqual(clean_feed_text("Tom & Jerry"), "Tom & Jerry")
        self.assertEqual(clean_feed_text("<b>Bold</b> and <i>Italic</i>"), "Bold and Italic")
        self.assertEqual(clean_feed_text("std::vector<int> & 3 < 5"), "std::vector<int> & 3 < 5")
        self.assertEqual(clean_feed_text("<![CDATA[Breaking: News]]>"), "Breaking: News")
        self.assertEqual(clean_feed_text("Multiple   spaces\n\nand \xa0nbsp"), "Multiple spaces and nbsp")
        self.assertEqual(clean_feed_text(None), "")
        self.assertEqual(clean_feed_text(""), "")


if __name__ == "__main__":
    unittest.main()
