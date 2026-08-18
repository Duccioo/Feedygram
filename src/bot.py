import os
import sys
import html
import random
import pathlib
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📖 My Feeds"), KeyboardButton("🔍 Explore Feeds")],
        [KeyboardButton("➕ Add Feed"), KeyboardButton("📥 Get Feeds")],
        [KeyboardButton("🗑️ Remove Feed"), KeyboardButton("⚙️ Keyword Filters")],
        [KeyboardButton("💾 Backup & OPML"), KeyboardButton("❓ Help & Info")],
    ],
    resize_keyboard=True,
)

# -----
from utils.database import DatabaseHandler
from utils.feedhandler import FeedHandler
from utils.make_text import bip_bop, random_emoji
from command.processing import BatchProcess
from command.other_commands import (
    list_handler,
    stop_handler,
    help_message,
    about_message,
)
import command.feed_message as feed_message
from command.important_command import remove_list_handler, get_list_handler
from providers import get_feed_provider, BaseFeedProvider
from utils.opml import export_opml, parse_opml
from utils.twitter import extract_twitter_username, get_candidate_twitter_rss_urls
from utils.youtube import get_youtube_rss_url
from utils.reddit import extract_reddit_target
from utils.summarizer import summarize_article
from utils.presets import (
    make_categories_keyboard,
    make_category_feeds_keyboard,
)


# Logging configuration
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
UPDATE_INTERVAL = os.environ.get("UPDATE_INTERVAL", "300")


def validate_callback_data(pattern: str):
    """Factory to create callback data validation functions"""
    def checker(callback_data: Any) -> bool:
        if isinstance(callback_data, dict):
            return callback_data.get("option") == pattern
        return False

    return checker


class Feedergraph(object):
    def __init__(self, telegram_token: str, update_interval: str):
        self._validate_config(telegram_token, update_interval)

        data_path = pathlib.Path(__file__).parent / "database" / "data"
        if not os.path.exists(data_path):
            os.makedirs(data_path, exist_ok=True)

        # Initialize bot internals
        self.db = DatabaseHandler("database", "data", "datastore.db")
        self.provider: BaseFeedProvider = get_feed_provider()

        self._init_bot(telegram_token)
        self._register_handlers()
        self._start_processing(update_interval)

    def _validate_config(self, token: str, interval: str) -> None:
        if not token:
            raise ValueError("Missing Telegram token. Set TELEGRAM_TOKEN in environment variables.")
        try:
            int(interval)
        except ValueError:
            raise ValueError("UPDATE_INTERVAL must be an integer (in seconds).")

    def _init_bot(self, token: str) -> None:
        self.bot = (
            Application.builder()
            .token(token)
            .concurrent_updates(True)
            .arbitrary_callback_data(True)
            .build()
        )
        self.job_queue = self.bot.job_queue

    def _register_handlers(self) -> None:
        handlers = [
            CommandHandler("start", self.start),
            CommandHandler("stop", self.stop),
            CommandHandler("help", self.help),
            CommandHandler("list", self.list),
            CommandHandler("about", self.about),
            CommandHandler("add", self.add),
            CommandHandler("get", self.get),
            CommandHandler("remove", self.remove),
            CommandHandler("export", self.export_feeds),
            CommandHandler("import", self.import_prompt),
            CommandHandler(["twitter", "x"], self.twitter_add),
            CommandHandler(["youtube", "yt"], self.youtube_add),
            CommandHandler(["reddit", "r"], self.reddit_add),
            CommandHandler("filter", self.filter_command),
            CommandHandler("channel", self.channel_command),
            CommandHandler(["explore", "presets", "popular"], self.explore_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_menu_text),
            MessageHandler(filters.Document.ALL, self.handle_document),
        ]

        callback_patterns = {
            "change_database": validate_callback_data("change_database"),
            "delete_feed": validate_callback_data("delete_feed"),
            "select_how_many_feed": validate_callback_data("select_how_many_feed"),
            "send_feed": validate_callback_data("send_feed"),
            "change_feed_link": validate_callback_data("change_feed_link"),
            "get_tldr": validate_callback_data("get_tldr"),
            "explore_category": validate_callback_data("explore_category"),
            "explore_categories": validate_callback_data("explore_categories"),
            "add_preset": validate_callback_data("add_preset"),
        }

        for pattern, handler in [
            (callback_patterns["change_database"], self.change_list_type),
            (callback_patterns["delete_feed"], self.remove),
            (callback_patterns["select_how_many_feed"], self.get),
            (callback_patterns["send_feed"], self.get_n_feed),
            (callback_patterns["change_feed_link"], self.update_message),
            (callback_patterns["get_tldr"], self.handle_tldr),
            (callback_patterns["explore_category"], self.handle_explore_category),
            (callback_patterns["explore_categories"], self.handle_explore_categories),
            (callback_patterns["add_preset"], self.handle_add_preset),
        ]:
            self.bot.add_handler(CallbackQueryHandler(handler, pattern=pattern))

        for handler in handlers:
            self.bot.add_handler(handler)

    def _start_processing(self, interval: str) -> None:
        try:
            interval_int = int(interval)
            self.processing = BatchProcess(
                database=self.db,
                update_interval=interval_int,
                bot=self.bot,
                provider=self.provider,
            )
            self.job_queue.run_repeating(self.processing.run, interval_int, first=1)
            logger.info("Bot and polling started successfully")
            self.bot.run_polling()
        except Exception as e:
            logger.critical(f"Bot startup error: {e}")
            raise

    async def start(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        try:
            if not self.db.get_user(user.id):
                await self._handle_new_user(update, user)
            else:
                self.db.update_user(user.id, is_active=1)
                await update.message.reply_text(
                    f"{bip_bop()}Welcome back! All set.{bip_bop()}\n\n"
                    "Use the buttons below to manage your feeds or send me a link directly!",
                    parse_mode="HTML",
                    reply_markup=MAIN_MENU_KEYBOARD,
                )
        except Exception as e:
            logger.error(f"Error during /start: {e}")
            await update.message.reply_text("Oops! Something went wrong while starting.")

    async def _handle_new_user(self, update, user: Any) -> None:
        welcome_msg = (
            "Hi👋! Welcome to <b>Feedygram</b>!\n\n"
            "Tap the buttons below to discover popular feeds, view your subscriptions, or send me any website URL to follow it instantly!\n\n"
            f"If you need help, tap <b>❓ Help & Info</b> or type <b>/help</b>.{bip_bop()}"
        )
        await update.message.reply_text(welcome_msg, parse_mode="HTML", reply_markup=MAIN_MENU_KEYBOARD)
        self.db.add_user(
            telegram_id=user.id,
            username=user.username,
            firstname=user.first_name,
            lastname=user.last_name,
            language_code=user.language_code,
            is_bot=user.is_bot,
            is_active=1,
        )


    async def update_message(self, update, context):
        """Updates a single feed message toggling link type (Normal vs Telegraph)"""
        query = update.callback_query
        if query is not None:
            await query.answer()
            data = query.data
            message, keyboard = feed_message.send_feed(
                telegraph=bool(data["set_telegraph"]),
                alias=data["alias"],
                post_link=data["link"],
                post_title=data["title"],
            )
            await query.edit_message_text(
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    async def change_list_type(self, update, context):
        """Updates user default link preference for a feed (Normal Link vs Telegraph)"""
        query = update.callback_query
        if query is not None:
            await query.answer()
            telegram_user = query.from_user
            data = query.data
            set_telegraph = bool(data["set_telegraph"])

            self.db.update_user_bookmark(
                telegram_user.id,
                url=data["url"],
                alias=data["alias"],
                telegraph=set_telegraph,
            )

            if set_telegraph:
                current_type = "🤙Telegraph Link🤙"
                next_type = "✳️Normal Link✳️"
            else:
                current_type = "✳️Normal Link✳️"
                next_type = "🤙Telegraph Link🤙"

            safe_alias = html.escape(str(data["alias"]))
            praise = random.choice(["Wonderful\n", "Marvelous\n", "Amazing\n"])
            message = (
                f"{praise}I changed '<b>{safe_alias}</b>' to send by default\n"
                f"<b>{current_type}</b>!\n\n"
                f"If you want to switch back to <b>{next_type}</b> click the button below!"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        f"🔙 Change to {next_type}",
                        callback_data={
                            "option": "change_database",
                            "alias": data["alias"],
                            "url": data["url"],
                            "set_telegraph": not set_telegraph,
                        },
                    )
                ],
            ]

            await query.edit_message_text(
                text=message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    async def add(self, update, context):
        """Adds a new RSS subscription for the user"""
        effective_user = update.effective_user or update.effective_chat
        chat_id = update.effective_chat.id
        msg = update.effective_message
        raw_text = msg.text.strip() if msg and msg.text else ""
        parts = raw_text.split(maxsplit=2)

        example_list = [
            "🍕Best site for cooking Pizza🍕",
            "🐶WoofWoof",
            "🎮Games&Tech🍹",
            "📰Daily News",
        ]

        if len(parts) < 2:
            message = (
                "Oh nono! I could not add the entry😯!\n"
                + bip_bop()
                + "I need <b>at least</b> a valid URL, and, if you want, a custom name.\n"
                + "Try to send a valid URL like this:\n\n"
                + f"<code>/add https://duccio.me/rss {random.choice(example_list)}</code>"
            )
            await msg.reply_text(message, parse_mode="HTML")
            return

        # Auto-detect special sources (Twitter, YouTube, Reddit)
        twitter_user = extract_twitter_username(parts[1])
        yt_feed_url = get_youtube_rss_url(parts[1])
        reddit_feed_url = extract_reddit_target(parts[1])

        if twitter_user:
            candidates = get_candidate_twitter_rss_urls(twitter_user)
            arg_url = candidates[0]
            for cand in candidates:
                is_ok, _ = self.provider.validate_feed(cand)
                if is_ok:
                    arg_url = cand
                    break
            arg_entry = parts[2].strip() if len(parts) >= 3 else f"🐦 @{twitter_user}"
        elif yt_feed_url:
            arg_url = yt_feed_url
            if len(parts) >= 3:
                arg_entry = parts[2].strip()
            else:
                yt_title = self.provider.get_feed_title(arg_url)
                arg_entry = f"▶️ {yt_title.strip()}" if yt_title else f"▶️ YouTube ({parts[1]})"
        elif reddit_feed_url:
            arg_url = reddit_feed_url
            if len(parts) >= 3:
                arg_entry = parts[2].strip()
            else:
                r_title = self.provider.get_feed_title(arg_url)
                arg_entry = f"🤖 {r_title.strip()}" if r_title else f"🤖 {parts[1]}"
        else:
            # Feed URL auto-discovery if user provided a website homepage or HTML page
            discovered = FeedHandler.discover_feed_url(parts[1])
            arg_url = discovered or FeedHandler.format_url_string(parts[1])

            # Validate feed via provider
            is_parsable, error_message = self.provider.validate_feed(arg_url)
            if not is_parsable:
                safe_url = html.escape(arg_url)
                safe_err = html.escape(str(error_message))
                user_friendly_message = (
                    f"{bip_bop()}Sorry! The URL <code>{safe_url}</code> is not a valid feed.\n"
                    f"<b>Reason:</b> {safe_err}\n\n"
                    "Please try another URL."
                )
                await msg.reply_text(user_friendly_message, parse_mode="HTML")
                return

            # Assign alias (custom or feed title)
            if len(parts) >= 3:
                arg_entry = parts[2].strip()
            else:
                feed_title = self.provider.get_feed_title(arg_url)
                if feed_title and feed_title.strip():
                    arg_entry = f"{random_emoji()} {feed_title.strip()}"
                else:
                    arg_entry = f"{random_emoji()} {arg_url}"

        user_entries = self.db.get_urls_for_user(telegram_id=chat_id)

        # Check if URL is already saved for this user
        if any(arg_url == entry[0] for entry in user_entries):
            user_name = getattr(effective_user, "first_name", None) or getattr(effective_user, "title", "Human")
            safe_name = html.escape(str(user_name))
            message = (
                f"Sorry, {safe_name}! I already have that URL stored in your subscriptions😒\n"
                f"Add a new one like this:\n"
                f"<code>/add https://duccio.me/rss {random.choice(example_list)}</code>"
            )
            await msg.reply_text(message, parse_mode="HTML")
            return

        # Check if alias is already used for this user
        if any(arg_entry == entry[1] for entry in user_entries):
            message = (
                "🤬<b>NOOOO!\nI ALREADY HAVE AN ENTRY WITH THAT NAME!!</b>\n\n"
                f"{bip_bop()} Try to choose a different custom name!"
            )
            await msg.reply_text(message, parse_mode="HTML")
            return

        self.db.add_user_bookmark(
            telegram_id=chat_id, url=arg_url, alias=arg_entry, telegraph=False
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔗 Change to Telegraph Link",
                    callback_data={
                        "option": "change_database",
                        "alias": arg_entry,
                        "url": arg_url,
                        "set_telegraph": True,
                    },
                )
            ],
        ]
        safe_alias = html.escape(arg_entry)
        message = (
            "WOOW!!🤝"
            f"{bip_bop()}\nI successfully added (<b>{safe_alias}</b>) to your subscriptions!"
            f"{bip_bop()}\n👀Look! By default when I find a new post I will send the <b>Normal Link</b>.\n"
            "If you want to receive <b>Telegraph Links</b> (to open with <u>Instant View</u>) click the button below!"
        )
        await msg.reply_text(
            text=message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def get_n_feed(self, update, context):
        """Sends the latest N articles for the selected feed"""
        query = update.callback_query
        if query is not None:
            await query.answer()
            data = query.data
            chat_id = data["user"]
            num_feeds = int(data.get("number_feed", 1))

            entries = self.provider.fetch_entries(data["url"], num_feeds)
            if not entries:
                safe_alias = html.escape(str(data.get("alias", "Feed")))
                message = (
                    f"{bip_bop()} mhh... I tried my best to fetch feeds for <b>{safe_alias}</b> but I couldn't.\n"
                    "Please check if the feed is still active."
                )
                await self.bot.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                )
                return

            db_bookmark = self.db.get_user_bookmark(chat_id, alias=data["alias"])
            use_telegraph = bool(db_bookmark[3]) if db_bookmark else False

            for entry in reversed(entries):
                post_title = entry.title or "No Title"
                post_link = entry.source_link or entry.link

                msg_text, reply_markup = feed_message.send_feed(
                    telegraph=use_telegraph,
                    alias=data["alias"],
                    post_link=post_link,
                    post_title=post_title,
                    tags=entry.tags,
                )

                await self.bot.bot.send_message(
                    chat_id=chat_id,
                    text=msg_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    link_preview_options=LinkPreviewOptions(prefer_small_media=True),
                )

    async def get(self, update, context):
        """Shows menu to manually request articles for a feed"""
        query = update.callback_query

        if query is not None:
            await query.answer()
            data = query.data
            safe_alias = html.escape(str(data["alias"]))
            message = (
                f"{bip_bop()} perfect👌\nSelect how many articles you want to receive for:\n\n"
                f"<b>{safe_alias}</b>\n"
            )
            keyboard_number_feed = [
                [
                    InlineKeyboardButton(
                        "1",
                        callback_data={
                            "option": "send_feed",
                            "alias": data["alias"],
                            "url": data["url"],
                            "user": data["user"],
                            "number_feed": 1,
                        },
                    ),
                    InlineKeyboardButton(
                        "5",
                        callback_data={
                            "option": "send_feed",
                            "alias": data["alias"],
                            "url": data["url"],
                            "user": data["user"],
                            "number_feed": 5,
                        },
                    ),
                    InlineKeyboardButton(
                        "10",
                        callback_data={
                            "option": "send_feed",
                            "alias": data["alias"],
                            "url": data["url"],
                            "user": data["user"],
                            "number_feed": 10,
                        },
                    ),
                ],
            ]

            await query.edit_message_text(
                text=message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard_number_feed),
            )
        else:
            effective_user = update.effective_user or update.effective_chat
            chat_id = update.effective_chat.id
            entries = self.db.get_urls_for_user(telegram_id=chat_id)
            get_list_message, get_list_keyboard = get_list_handler(
                feed_list=entries, telegram_user=effective_user
            )
            await update.effective_message.reply_text(
                text=get_list_message,
                parse_mode="HTML",
                reply_markup=get_list_keyboard,
            )

    async def remove(self, update, context):
        """Shows the list of saved feeds allowing removal"""
        query = update.callback_query

        if query is not None:
            await query.answer()
            effective_user = query.from_user
            chat_id = query.from_user.id
            data = query.data
            self.db.remove_user_bookmark(telegram_id=chat_id, url=data["url"])
        else:
            effective_user = update.effective_user or update.effective_chat
            chat_id = update.effective_chat.id

        entries = self.db.get_urls_for_user(telegram_id=chat_id)
        remove_list_message, remove_list_keyboard = remove_list_handler(
            feed_list=entries, telegram_user=effective_user
        )

        if query is not None:
            await query.edit_message_text(
                text=remove_list_message,
                parse_mode="HTML",
                reply_markup=remove_list_keyboard,
            )
        else:
            await update.effective_message.reply_text(
                text=remove_list_message,
                parse_mode="HTML",
                reply_markup=remove_list_keyboard,
            )

    async def list(self, update, context):
        """Shows all registered feeds with option to toggle link mode"""
        chat_id = update.effective_chat.id
        entries = self.db.get_urls_for_user(telegram_id=chat_id)

        if not entries:
            await update.effective_message.reply_text(
                f"{bip_bop()} You don't have any subscriptions yet! Use <b>/add</b> to add one.",
                parse_mode="HTML",
            )
            return

        header_message = (
            f"{bip_bop()}🤖! Here is the list of your subscriptions ❤️!\n"
            "Click on a button to toggle between Normal Link and Telegraph:"
        )
        await update.effective_message.reply_text(header_message, parse_mode="HTML")

        for index, entry in enumerate(entries):
            is_telegraph = bool(entry[5]) if len(entry) > 5 else False
            item_msg, item_keyboard = list_handler(
                db_telegraph=is_telegraph, alias=entry[1], url=entry[0], index=index
            )
            await update.effective_message.reply_text(
                text=item_msg,
                parse_mode="HTML",
                reply_markup=item_keyboard,
            )

    async def help(self, update, context):
        """Sends help message with quick start keyboard"""
        await update.effective_message.reply_text(
            help_message(),
            parse_mode="HTML",
            reply_markup=MAIN_MENU_KEYBOARD,
        )

    async def stop(self, update, context):
        """Deactivates feed updates for the user"""
        user = update.effective_user or update.effective_chat
        await update.effective_message.reply_text(
            stop_handler(telegram_user=user, db=self.db),
            parse_mode="HTML",
        )

    async def about(self, update, context):
        """Shows information about the bot"""
        message = about_message(number=self.db.get_total_users(active_only=True))
        await update.effective_message.reply_text(text=message, parse_mode="HTML")


    async def export_feeds(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Exports all user subscriptions to an OPML file"""
        chat_id = update.effective_chat.id
        entries = self.db.get_urls_for_user(telegram_id=chat_id)
        if not entries:
            await update.effective_message.reply_text(
                f"{bip_bop()} You don't have any saved feeds to export yet! Use <b>/add</b> to add one.",
                parse_mode="HTML",
            )
            return

        opml_buffer = export_opml(entries)
        await context.bot.send_document(
            chat_id=chat_id,
            document=opml_buffer,
            filename="feedygram_subscriptions.opml",
            caption=f"📦 Here is the backup of your <b>{len(entries)}</b> feeds in OPML format!",
            parse_mode="HTML",
        )

    async def import_prompt(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends instructions for importing an OPML file"""
        message = (
            f"{bip_bop()} <b>Feed Import (OPML)</b>\n\n"
            "Send a <code>.opml</code> or <code>.xml</code> file directly into this chat "
            "and I will automatically import all feeds for you!"
        )
        await update.effective_message.reply_text(message, parse_mode="HTML")

    async def handle_document(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles OPML file uploads to import subscriptions"""
        doc = update.effective_message.document if update.effective_message else None
        if not doc or not doc.file_name:
            return

        file_name = doc.file_name.lower()
        if not (file_name.endswith(".opml") or file_name.endswith(".xml")):
            return

        chat_id = update.effective_chat.id
        status_msg = await update.effective_message.reply_text(f"{bip_bop()} Analyzing OPML file...")

        try:
            tg_file = await context.bot.get_file(doc.file_id)
            file_bytes = await tg_file.download_as_bytearray()
            parsed_feeds = parse_opml(bytes(file_bytes))

            if not parsed_feeds:
                await status_msg.edit_text(f"{bip_bop()} No valid feeds found in the provided OPML file.")
                return

            existing = {entry[0] for entry in self.db.get_urls_for_user(telegram_id=chat_id)}
            added = 0
            skipped = 0

            for url, title in parsed_feeds:
                formatted_url = FeedHandler.format_url_string(url)
                if formatted_url in existing:
                    skipped += 1
                    continue

                is_valid, _ = self.provider.validate_feed(formatted_url)
                if is_valid:
                    alias = f"{random_emoji()} {title}" if title else f"{random_emoji()} {formatted_url}"
                    self.db.add_user_bookmark(telegram_id=chat_id, url=formatted_url, alias=alias, telegraph=False)
                    existing.add(formatted_url)
                    added += 1
                else:
                    skipped += 1

            result_msg = (
                f"🎉 <b>Import completed!</b>\n\n"
                f"✅ Feeds added: <b>{added}</b>\n"
                f"⏭️ Feeds skipped or duplicate: <b>{skipped}</b>\n\n"
                "Use <b>/list</b> to see your updated subscriptions."
            )
            await status_msg.edit_text(result_msg, parse_mode="HTML")

        except Exception as e:
            logger.error(f"OPML import error: {e}")
            await status_msg.edit_text(f"❌ Error while importing OPML file: {e}")

    async def twitter_add(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Quick command to follow a Twitter / X account"""
        msg = update.effective_message
        raw_text = msg.text.strip() if msg and msg.text else ""
        parts = raw_text.split(maxsplit=2)
        if len(parts) < 2:
            await msg.reply_text(
                f"{bip_bop()} To follow a Twitter / X account use:\n\n"
                "<code>/x @username</code> or <code>/twitter @username</code>\n"
                "<i>(Optional)</i> with custom name: <code>/x @username My Channel</code>",
                parse_mode="HTML",
            )
            return
        await self.add(update, context)

    async def youtube_add(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Quick command to follow a YouTube channel or playlist"""
        msg = update.effective_message
        raw_text = msg.text.strip() if msg and msg.text else ""
        parts = raw_text.split(maxsplit=2)
        if len(parts) < 2:
            await msg.reply_text(
                f"{bip_bop()} To follow a YouTube channel or playlist use:\n\n"
                "<code>/youtube @channelname</code> or <code>/yt https://youtube.com/@handle</code>",
                parse_mode="HTML",
            )
            return
        await self.add(update, context)

    async def reddit_add(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Quick command to follow a Reddit subreddit or user"""
        msg = update.effective_message
        raw_text = msg.text.strip() if msg and msg.text else ""
        parts = raw_text.split(maxsplit=2)
        if len(parts) < 2:
            await msg.reply_text(
                f"{bip_bop()} To follow a Reddit subreddit or user use:\n\n"
                "<code>/reddit r/technology</code> or <code>/r python</code>",
                parse_mode="HTML",
            )
            return
        await self.add(update, context)

    async def filter_command(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles configuring keyword filters for a feed"""
        chat_id = update.effective_chat.id
        msg = update.effective_message
        raw_text = msg.text.strip() if msg and msg.text else ""
        entries = self.db.get_urls_for_user(telegram_id=chat_id)

        if not entries:
            await msg.reply_text(f"{bip_bop()} You don't have any saved feeds yet.")
            return

        cmd_parts = raw_text.split(maxsplit=1)
        if len(cmd_parts) < 2:
            lines = ["<b>🔍 Active keyword filters:</b>\n"]
            for i, entry in enumerate(entries):
                alias = entry[1]
                rules = entry[4] if len(entry) > 4 and entry[4] else "<i>no filters</i>"
                lines.append(f"{i + 1}️⃣ • <b>{html.escape(alias)}</b>: <code>{html.escape(rules)}</code>")

            lines.append("\n<b>How to set a filter:</b>")
            lines.append("<code>/filter [Number or Name] +include -exclude</code>")
            lines.append("<i>Example with number:</i> <code>/filter 1 +Python -Crypto</code>")
            lines.append("<i>Example with name:</i> <code>/filter \"TechNews\" +Python -Crypto</code>")
            lines.append("<i>To reset:</i> <code>/filter 1 reset</code>")
            await msg.reply_text("\n".join(lines), parse_mode="HTML")
            return

        rest = cmd_parts[1].strip()
        target_alias = None
        rules = ""

        # Support selection by index number
        parts = rest.split(maxsplit=1)
        if parts[0].isdigit():
            idx = int(parts[0]) - 1
            if 0 <= idx < len(entries):
                target_alias = entries[idx][1]
                rules = parts[1].strip() if len(parts) > 1 else ""
        elif rest.startswith(('"', "'")):
            quote_char = rest[0]
            end_quote = rest.find(quote_char, 1)
            if end_quote != -1:
                target_alias = rest[1:end_quote].strip()
                rules = rest[end_quote + 1:].strip()

        if target_alias is None:
            # Match existing alias prefix
            for entry in entries:
                alias = entry[1]
                if rest.startswith(alias) or rest.lower().startswith(alias.lower()):
                    target_alias = alias
                    rules = rest[len(alias):].strip()
                    break

        if target_alias is None:
            parts2 = rest.split(maxsplit=1)
            target_alias = parts2[0]
            rules = parts2[1].strip() if len(parts2) > 1 else ""

        if rules.lower() == "reset":
            rules = ""

        updated = self.db.update_user_bookmark_filter(chat_id, target_alias, rules)
        if updated:
            if rules:
                await msg.reply_text(
                    f"✅ Filters updated for <b>{html.escape(target_alias)}</b>:\n<code>{html.escape(rules)}</code>",
                    parse_mode="HTML",
                )
            else:
                await msg.reply_text(
                    f"✅ Filters removed for <b>{html.escape(target_alias)}</b>. You will receive all articles.",
                    parse_mode="HTML",
                )
        else:
            await msg.reply_text(
                f"❌ No feed found with the name <b>{html.escape(target_alias)}</b>. Check with <b>/list</b> or <b>/filter</b>.",
                parse_mode="HTML",
            )

    async def channel_command(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Instructions to forward notifications to Telegram channels and groups"""
        msg = (
            f"{bip_bop()} <b>Forward Notifications to Channels & Groups</b>\n\n"
            "To publish news to a channel or group:\n\n"
            "1️⃣ Add this bot as an <b>Administrator</b> in your channel or group.\n"
            "2️⃣ Send the <code>/add</code> command directly inside the channel/group!\n"
            "   <i>Example:</i> <code>/add https://duccio.me/rss TechNews</code>\n\n"
            "The bot will automatically post all new articles there! 🚀"
        )
        await update.effective_message.reply_text(msg, parse_mode="HTML")

    async def handle_tldr(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generates and applies TL;DR by editing the feed message in-place"""
        query = update.callback_query
        if query is not None:
            await query.answer("Generating summary...")
            data = query.data
            link = data.get("link", "")
            title = data.get("title", "")
            alias = data.get("alias", "Feed")

            summary = summarize_article(link, title=title)
            safe_title = html.escape(str(title).strip() if title else "Article")
            safe_alias = html.escape(str(alias).strip())
            safe_summary = html.escape(summary)

            # Edit message in-place adding summary
            msg = (
                f"<b>{safe_alias}</b>\n"
                f"<a href='{link}'><b>{safe_title}</b></a>\n\n"
                f"📝 <b>TL;DR:</b>\n"
                f"<i>{safe_summary}</i>"
            )

            # Remove TL;DR button from keyboard while keeping link toggle
            new_keyboard = []
            if query.message and query.message.reply_markup:
                for row in query.message.reply_markup.inline_keyboard:
                    filtered_row = [
                        btn for btn in row
                        if getattr(btn, "callback_data", None) and isinstance(btn.callback_data, dict) and btn.callback_data.get("option") != "get_tldr"
                    ]
                    if filtered_row:
                        new_keyboard.append(filtered_row)

            try:
                await query.edit_message_text(
                    text=msg,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(new_keyboard) if new_keyboard else None,
                    link_preview_options=LinkPreviewOptions(prefer_small_media=True),
                )
            except Exception as e:
                logger.warning("Unable to edit message in handle_tldr: %s", e)
                await query.message.reply_text(
                    text=msg,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )

    async def explore_command(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Shows popular feeds catalog categorized by topic"""
        msg = update.effective_message
        text = (
            f"{bip_bop()} <b>Explore Popular Feeds</b>\n\n"
            "Select a category to discover and add popular feeds with one click:"
        )
        await msg.reply_text(
            text=text,
            parse_mode="HTML",
            reply_markup=make_categories_keyboard(),
        )

    async def handle_explore_category(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Shows feeds for a specific category in preset catalog"""
        query = update.callback_query
        if query is not None:
            await query.answer()
            cat = query.data.get("cat", "")
            msg_text, reply_markup = make_category_feeds_keyboard(cat)
            await query.edit_message_text(
                text=msg_text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

    async def handle_explore_categories(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Returns to preset categories list"""
        query = update.callback_query
        if query is not None:
            await query.answer()
            text = (
                f"{bip_bop()} <b>Explore Popular Feeds</b>\n\n"
                "Select a category to discover and add popular feeds with one click:"
            )
            await query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=make_categories_keyboard(),
            )

    async def handle_add_preset(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Adds selected preset feed with one click"""
        query = update.callback_query
        if query is not None:
            await query.answer()
            chat_id = query.from_user.id
            data = query.data
            url = data.get("url", "")
            name = data.get("name", "Feed")
            alias = f"{random_emoji()} {name}"

            user_entries = self.db.get_urls_for_user(telegram_id=chat_id)
            if any(url == entry[0] for entry in user_entries):
                await query.message.reply_text(
                    f"You are already subscribed to <b>{html.escape(name)}</b>!",
                    parse_mode="HTML",
                )
                return

            self.db.add_user_bookmark(
                telegram_id=chat_id, url=url, alias=alias, telegraph=False
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔗 Change to Telegraph Link",
                        callback_data={
                            "option": "change_database",
                            "alias": alias,
                            "url": url,
                            "set_telegraph": True,
                        },
                    )
                ]
            ]
            await query.message.reply_text(
                f"🎉 Successfully added: <b>{html.escape(alias)}</b>!\n"
                f"You will automatically receive notifications for new articles.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    async def handle_menu_text(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles actions from reply keyboard menu buttons or direct URL input"""
        text = (update.effective_message.text or "").strip()
        if not text:
            return

        if text in ["📖 My Feeds", "My Feeds", "📖 I Miei Feed", "I Miei Feed"]:
            await self.list(update, context)
        elif text in ["🔍 Explore Feeds", "Explore Feeds", "🔍 Esplora Feed", "Esplora Feed"]:
            await self.explore_command(update, context)
        elif text in ["➕ Add Feed", "Add Feed", "➕ Aggiungi Feed", "Aggiungi Feed"]:
            msg = (
                f"{bip_bop()} <b>How to add a Feed:</b>\n\n"
                "1️⃣ <b>Paste any link:</b> send the URL of any website, blog, or RSS feed directly in this chat!\n"
                "<i>(Example: <code>https://theverge.com</code>)</i>\n\n"
                "2️⃣ <b>Social & Media:</b>\n"
                "• YouTube: <code>/youtube @channelname</code>\n"
                "• Reddit: <code>/reddit r/subreddit_name</code>\n"
                "• X / Twitter: <code>/x @username</code>\n\n"
                "3️⃣ Or use <b>/add</b> with a custom name:\n"
                "<code>/add https://duccio.me/rss My Blog</code>"
            )
            await update.effective_message.reply_text(msg, parse_mode="HTML", reply_markup=MAIN_MENU_KEYBOARD)
        elif text in ["📥 Get Feeds", "Get Feeds", "📥 Scarica Notizie", "Scarica Notizie"]:
            await self.get(update, context)
        elif text in ["🗑️ Remove Feed", "Remove Feed", "🗑️ Rimuovi Feed", "Rimuovi Feed"]:
            await self.remove(update, context)
        elif text in ["⚙️ Keyword Filters", "Keyword Filters", "⚙️ Filtri Parole", "Filtri Parole"]:
            await self.filter_command(update, context)
        elif text in ["💾 Backup & OPML", "Backup & OPML"]:
            msg = (
                f"{bip_bop()} <b>Backup & OPML Management</b>\n\n"
                "• To <b>export</b> all your feeds in standard OPML format use <code>/export</code>\n"
                "• To <b>import</b> an OPML file send the <code>.opml</code> or <code>.xml</code> file directly in this chat!"
            )
            await update.effective_message.reply_text(msg, parse_mode="HTML", reply_markup=MAIN_MENU_KEYBOARD)
        elif text in ["❓ Help & Info", "Help & Info", "❓ Aiuto & Info", "Aiuto & Info"]:
            await self.help(update, context)
        elif text.startswith("http://") or text.startswith("https://"):
            # User pasted a URL directly: add with auto-discovery
            context.args = text.split()
            await self.add(update, context)


if __name__ == "__main__":
    Feedergraph(telegram_token=TELEGRAM_TOKEN, update_interval=UPDATE_INTERVAL)


