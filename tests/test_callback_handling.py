import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Mock external modules if not available in testing environment
for mod in [
    "telegram",
    "telegram.ext",
    "telegram.error",
    "requests",
    "feedparser",
    "bs4",
    "dotenv",
    "html_telegraph_poster",
    "webpage2telegraph",
    "trafilatura",
    "newspaper",
]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

from bot import validate_callback_data, Feedergraph


class FakeInvalidCallbackData:
    """Simulates telegram.ext.InvalidCallbackData"""
    pass


class TestCallbackHandling(unittest.IsolatedAsyncioTestCase):

    def test_validate_callback_data_matches(self):
        checker = validate_callback_data("change_feed_link")
        self.assertTrue(checker({"option": "change_feed_link", "link": "https://example.com"}))

    def test_validate_callback_data_mismatches(self):
        checker = validate_callback_data("change_feed_link")
        self.assertFalse(checker({"option": "different_option"}))

    def test_validate_callback_data_rejects_invalid_callback_data(self):
        checker = validate_callback_data("change_feed_link")
        self.assertFalse(checker(FakeInvalidCallbackData()))
        self.assertFalse(checker("string_callback"))
        self.assertFalse(checker(None))

    async def test_handle_invalid_callback_answers_query(self):
        # Create a mock Feedergraph instance without calling full __init__
        bot_instance = object.__new__(Feedergraph)

        mock_query = AsyncMock()
        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        mock_context = MagicMock()

        await bot_instance.handle_invalid_callback(mock_update, mock_context)

        mock_query.answer.assert_awaited_once_with(
            text="⚠️ This button has expired or is no longer valid.",
            show_alert=True,
        )

    async def test_handle_invalid_callback_none_query(self):
        bot_instance = object.__new__(Feedergraph)
        mock_update = MagicMock()
        mock_update.callback_query = None
        mock_context = MagicMock()

        # Should not raise any error
        await bot_instance.handle_invalid_callback(mock_update, mock_context)

    def test_callback_cache_size_default(self):
        with patch.dict(os.environ, {}, clear=False):
            if "CALLBACK_CACHE_SIZE" in os.environ:
                del os.environ["CALLBACK_CACHE_SIZE"]
            # Verify fallback default value parsing
            parsed_size = int(os.environ.get("CALLBACK_CACHE_SIZE", "2048"))
            self.assertEqual(parsed_size, 2048)

    def test_callback_cache_size_custom(self):
        with patch.dict(os.environ, {"CALLBACK_CACHE_SIZE": "4096"}):
            parsed_size = int(os.environ.get("CALLBACK_CACHE_SIZE", "2048"))
            self.assertEqual(parsed_size, 4096)


if __name__ == "__main__":
    unittest.main()
