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
from command.other_commands import list_handler


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

    def test_list_handler_hides_telegraph_toggle_for_normal_users(self):
        msg, kb = list_handler(
            db_telegraph=False,
            alias="TechFeed",
            url="https://example.com/rss",
            index=0,
            allow_telegraph_toggle=False,
        )
        self.assertIn("TechFeed", msg)
        self.assertNotIn("Default link type", msg)
        self.assertIsNone(kb)

    def test_list_handler_shows_telegraph_toggle_for_admins(self):
        msg, kb = list_handler(
            db_telegraph=False,
            alias="TechFeed",
            url="https://example.com/rss",
            index=0,
            allow_telegraph_toggle=True,
        )
        self.assertIn("Default link type", msg)
        self.assertIsNotNone(kb)

    async def test_change_list_type_blocks_normal_user(self):
        bot_instance = object.__new__(Feedergraph)
        bot_instance.db = MagicMock()

        mock_query = AsyncMock()
        mock_query.from_user = MagicMock(id=2222)
        mock_query.data = {
            "option": "change_database",
            "alias": "MyFeed",
            "url": "https://example.com/rss",
            "set_telegraph": True,
        }
        mock_update = MagicMock(callback_query=mock_query)
        mock_context = MagicMock()

        with patch.dict(os.environ, {"ADMIN_USER_ID": "9999"}):
            await bot_instance.change_list_type(mock_update, mock_context)

        bot_instance.db.update_user_bookmark.assert_called_once_with(
            2222,
            url="https://example.com/rss",
            alias="MyFeed",
            telegraph=False,
        )
        mock_query.edit_message_text.assert_not_awaited()

    async def test_update_message_allows_on_demand_telegraph_for_any_user(self):
        bot_instance = object.__new__(Feedergraph)

        mock_query = AsyncMock()
        mock_query.data = {
            "option": "change_feed_link",
            "set_telegraph": True,
            "alias": "MyFeed",
            "link": "https://example.com/post",
            "title": "Post Title",
        }
        mock_update = MagicMock(callback_query=mock_query)
        mock_context = MagicMock()

        with patch("command.feed_message.send_feed", return_value=("Converted HTML", "MockKB")) as mock_send_feed:
            await bot_instance.update_message(mock_update, mock_context)

        mock_send_feed.assert_called_once_with(
            telegraph=True,
            alias="MyFeed",
            post_link="https://example.com/post",
            post_title="Post Title",
        )
        mock_query.edit_message_text.assert_awaited_once_with(
            text="Converted HTML",
            parse_mode="HTML",
            reply_markup="MockKB",
        )

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
