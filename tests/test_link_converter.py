import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from utils.link_converter import (
    ALLOWED_TAGS,
    clean_and_convert_html_to_nodes,
    _get_telegraph_token,
    _post_to_telegraph,
    convert_to_instant_link,
    transfer,
)


class TestLinkConverter(unittest.TestCase):
    def test_allowed_tags_constants(self):
        self.assertIn("p", ALLOWED_TAGS)
        self.assertIn("figure", ALLOWED_TAGS)
        self.assertIn("h3", ALLOWED_TAGS)
        self.assertNotIn("h1", ALLOWED_TAGS)
        self.assertNotIn("table", ALLOWED_TAGS)
        self.assertNotIn("div", ALLOWED_TAGS)

    def test_clean_and_convert_html_to_nodes_basic(self):
        html = """
        <h1>Main Heading</h1>
        <h2>Sub Heading</h2>
        <p>This is a paragraph with <b>bold</b>, <i>italic</i>, and <a href="https://example.com">a link</a>.</p>
        <ul>
            <li>First item</li>
            <li>Second item</li>
        </ul>
        """
        nodes = clean_and_convert_html_to_nodes(html, base_url="https://example.com")
        self.assertTrue(len(nodes) >= 3)

        tags = [n.get("tag") for n in nodes if isinstance(n, dict)]
        self.assertIn("h3", tags)
        self.assertNotIn("h1", tags)
        self.assertNotIn("h2", tags)
        self.assertIn("p", tags)
        self.assertIn("ul", tags)

    def test_clean_and_convert_html_to_nodes_unsupported_tags(self):
        html = """
        <script>alert('xss')</script>
        <style>body { color: red; }</style>
        <svg><path d="M0 0"/></svg>
        <form><input type="text"><button>Submit</button></form>
        <article>
            <section>
                <div>
                    <p>Clean text inside nested containers with <span>styled span</span> and <time>2026-09-03</time>.</p>
                </div>
            </section>
        </article>
        """
        nodes = clean_and_convert_html_to_nodes(html, base_url="https://example.com")

        # None of the dangerous/unsupported tags should exist as tag in output
        def _get_all_tags(node_list):
            found = set()
            for n in node_list:
                if isinstance(n, dict):
                    found.add(n.get("tag"))
                    if "children" in n:
                        found.update(_get_all_tags(n["children"]))
            return found

        all_tags = _get_all_tags(nodes)
        for disallowed in ["script", "style", "svg", "form", "button", "input", "article", "section", "div", "span", "time"]:
            self.assertNotIn(disallowed, all_tags)

        # Content should still be preserved
        json_str = json.dumps(nodes)
        self.assertIn("Clean text inside nested containers", json_str)
        self.assertNotIn("alert", json_str)

    def test_table_conversion(self):
        html = """
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Row 1 Col 1</td><td>Row 1 Col 2</td></tr>
        </table>
        """
        nodes = clean_and_convert_html_to_nodes(html, base_url="https://example.com")
        tags = [n.get("tag") for n in nodes if isinstance(n, dict)]
        self.assertNotIn("table", tags)
        self.assertIn("blockquote", tags)

        bq_node = next(n for n in nodes if isinstance(n, dict) and n.get("tag") == "blockquote")
        bq_text = json.dumps(bq_node)
        self.assertIn("Header 1 | Header 2", bq_text)
        self.assertIn("Row 1 Col 1 | Row 1 Col 2", bq_text)

    def test_image_sanitization(self):
        html = """
        <div>
            <!-- Base64 image to drop -->
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" alt="drop me"/>
            <!-- Lazy-loaded image -->
            <img src="/placeholder.png" data-src="/images/real_photo.jpg" alt="real"/>
            <!-- Normal image with relative url -->
            <img src="pic.jpg" alt="pic"/>
        </div>
        """
        nodes = clean_and_convert_html_to_nodes(html, base_url="https://example.com/article/")
        json_str = json.dumps(nodes)

        self.assertNotIn("data:image", json_str)
        self.assertIn("https://example.com/images/real_photo.jpg", json_str)
        self.assertIn("https://example.com/article/pic.jpg", json_str)

    def test_size_limit_truncation(self):
        # Create a huge HTML with 200 paragraphs
        paragraphs = "".join(f"<p>Paragraph {i}: {'a' * 500}</p>" for i in range(200))
        nodes = clean_and_convert_html_to_nodes(paragraphs, base_url="https://example.com/huge")

        total_bytes = len(json.dumps(nodes, ensure_ascii=False).encode("utf-8"))
        # Telegraph limit is 64KB, our truncation caps it well below 55KB
        self.assertLess(total_bytes, 55000)
        # Footer link should be appended
        self.assertIn("https://example.com/huge", json.dumps(nodes))

    @patch("requests.post")
    def test_post_to_telegraph(self, mock_post):
        mock_post.return_value.json.return_value = {
            "ok": True,
            "result": {"url": "https://telegra.ph/Test-Title-09-03"},
        }

        nodes = [{"tag": "p", "children": ["Hello world"]}]
        with patch("utils.link_converter._get_telegraph_token", return_value="fake_token_123"):
            res = _post_to_telegraph(
                title="Test Title",
                nodes=nodes,
                author_name="Feedygram",
                author_url="https://example.com",
            )
            self.assertEqual(res, "https://telegra.ph/Test-Title-09-03")
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            self.assertEqual(call_kwargs["json"]["access_token"], "fake_token_123")
            self.assertEqual(call_kwargs["json"]["title"], "Test Title")

    @patch("requests.post")
    def test_get_telegraph_token_creation_and_db(self, mock_post):
        mock_post.return_value.json.return_value = {
            "ok": True,
            "result": {"access_token": "new_created_token_xyz"},
        }

        import utils.link_converter as lc
        lc._telegraph_token = None

        with patch.dict("os.environ", {}, clear=True), patch("utils.database.DatabaseHandler") as mock_db_cls:
            mock_db = MagicMock()
            mock_db.get_setting.return_value = None
            mock_db_cls.return_value = mock_db

            token = _get_telegraph_token()
            self.assertEqual(token, "new_created_token_xyz")
            mock_db.set_setting.assert_called_with("telegraph_token", "new_created_token_xyz")

    @patch("utils.link_converter._post_to_telegraph")
    def test_tier1_feed_summary_fast_path(self, mock_post):
        mock_post.return_value = "https://telegra.ph/RSS-Article-09-03"

        long_summary = (
            "<p>This is a sufficiently long and rich article description from the RSS feed. "
            "It contains multiple detailed sentences providing full coverage of the news item, "
            "so there is no need to crawl the original website.</p>"
        )

        res = convert_to_instant_link(
            url="https://example.com/post-1",
            title="RSS Title",
            fallback_content=long_summary,
        )
        self.assertEqual(res, "https://telegra.ph/RSS-Article-09-03")
        mock_post.assert_called_once()

    @patch("utils.link_converter._post_to_telegraph")
    def test_fallback_to_original_url_on_failure(self, mock_post):
        mock_post.return_value = None

        with patch("requests.get", side_effect=Exception("Connection refused")):
            res = convert_to_instant_link(
                url="https://example.com/unreachable-post",
                title="Unreachable",
                fallback_content="",
            )
            self.assertEqual(res, "https://example.com/unreachable-post")

    def test_transfer_drop_in(self):
        with patch("utils.link_converter.convert_to_instant_link", return_value="https://telegra.ph/Drop-In-09-03"):
            res = transfer("https://example.com/test")
            self.assertEqual(res, "https://telegra.ph/Drop-In-09-03")


if __name__ == "__main__":
    unittest.main()
