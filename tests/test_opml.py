import os
import sys
import unittest
from pathlib import Path

# Add src to pythonpath
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.opml import export_opml, parse_opml


class TestOPML(unittest.TestCase):
    def test_export_and_parse_opml(self):
        feeds = [
            ("https://duccio.me/rss", "Duccio Blog"),
            ("https://news.ycombinator.com/rss", "Hacker News"),
        ]

        opml_buf = export_opml(feeds)
        content = opml_buf.getvalue()

        self.assertIn(b"xmlUrl=\"https://duccio.me/rss\"", content)
        self.assertIn(b"title=\"Duccio Blog\"", content)
        self.assertIn(b"xmlUrl=\"https://news.ycombinator.com/rss\"", content)

        parsed = parse_opml(content)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0][0], "https://duccio.me/rss")
        self.assertEqual(parsed[0][1], "Duccio Blog")
        self.assertEqual(parsed[1][0], "https://news.ycombinator.com/rss")
        self.assertEqual(parsed[1][1], "Hacker News")

    def test_parse_opml_attribute_variations(self):
        opml_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="1.0">
            <head><title>My Feeds</title></head>
            <body>
                <outline text="Reddit Tech" xmlurl="https://www.reddit.com/r/tech/.rss" />
                <outline title="Direct URL" url="https://example.com/feed" />
            </body>
        </opml>"""
        parsed = parse_opml(opml_xml)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0][0], "https://www.reddit.com/r/tech/.rss")
        self.assertEqual(parsed[0][1], "Reddit Tech")
        self.assertEqual(parsed[1][0], "https://example.com/feed")
        self.assertEqual(parsed[1][1], "Direct URL")

    def test_parse_invalid_opml(self):
        with self.assertRaises(ValueError):
            parse_opml(b"not valid xml content")


if __name__ == "__main__":
    unittest.main()
