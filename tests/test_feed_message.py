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


if __name__ == "__main__":
    unittest.main()
