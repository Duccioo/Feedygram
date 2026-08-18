import sys
import unittest
from pathlib import Path

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.summarizer import _extractive_summarize, summarize_article


class TestSummarizer(unittest.TestCase):
    def test_extractive_summarizer_basic(self):
        sample_text = (
            "Python is a popular general-purpose programming language. "
            "It emphasizes code readability with notable use of significant whitespace. "
            "Python is dynamically typed and garbage-collected. "
            "It supports multiple programming paradigms including structured, object-oriented and functional programming. "
            "Many developers love Python for artificial intelligence and scientific computing applications."
        )

        summary = _extractive_summarize(sample_text, max_sentences=3)
        self.assertTrue(summary.startswith("• "))
        self.assertIn("Python", summary)

    def test_summarize_html_content(self):
        html_input = (
            "<p>Artificial Intelligence is transforming software development rapidly.</p>"
            "<div>Developers are writing code faster with modern AI assistant tools.</div>"
            "<p>Tests and quality assurance are also benefiting from automated verification.</p>"
        )
        summary = _extractive_summarize(html_input, max_sentences=2)
        self.assertNotIn("<p>", summary)
        self.assertNotIn("<div>", summary)
        self.assertTrue(summary.startswith("• "))


if __name__ == "__main__":
    unittest.main()
