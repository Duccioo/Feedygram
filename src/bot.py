# /bin/bash/python
# encoding: utf-8


from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
import os
import logging
from dotenv import load_dotenv
import random
import pathlib
from typing import Any, Dict

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


# Configurazione logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv(override=True)
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
UPDATE_INTERVAL = os.environ["UPDATE_INTERVAL"]


def validate_callback_data(pattern: str):
    """Factory per creare funzioni di validazione callback data"""

    def checker(callback_data: Dict[str, Any]) -> bool:
        return callback_data.get("option") == pattern

    return checker


class Feedergraph(object):
    def __init__(self, telegram_token, update_interval):

        data_path = pathlib.Path(__file__).parent / "database" / "data"
        if not os.path.exists(data_path):
            os.makedirs(data_path)

        # Initialize bot internals
        self.db = DatabaseHandler("database", "data", "datastore.db")

        self._init_bot(telegram_token)
        self._register_handlers()
        self._start_processing(update_interval)

    def _validate_config(self, token: str, interval: str) -> None:
        if not token:
            raise ValueError("Telegram token mancante")
        try:
            int(interval)
        except ValueError:
            raise ValueError("UPDATE_INTERVAL deve essere un intero")

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
        ]

        callback_patterns = {
            "change_database": validate_callback_data("change_database"),
            "delete_feed": validate_callback_data("delete_feed"),
            "select_how_many_feed": validate_callback_data("select_how_many_feed"),
            "send_feed": validate_callback_data("send_feed"),
            "change_feed_link": validate_callback_data("change_feed_link"),
        }

        for pattern, handler in [
            (callback_patterns["change_database"], self.change_list_type),
            (callback_patterns["delete_feed"], self.remove),
            (callback_patterns["select_how_many_feed"], self.get),
            (callback_patterns["send_feed"], self.get_n_feed),
            (callback_patterns["change_feed_link"], self.update_message),
        ]:
            self.bot.add_handler(CallbackQueryHandler(handler, pattern=pattern))

        for handler in handlers:
            self.bot.add_handler(handler)

    def _start_processing(self, interval: str) -> None:
        try:
            interval_int = int(interval)
            self.processing = BatchProcess(
                database=self.db, update_interval=interval_int, bot=self.bot
            )
            self.job_queue.run_repeating(self.processing.run, interval_int, first=1)
            logger.info("Bot avviato correttamente")
            self.bot.run_polling()
        except Exception as e:
            logger.critical(f"Errore avvio bot: {e}")
            raise

    async def start(self, update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        try:
            if not self.db.get_user(user.id):
                await self._handle_new_user(update, user)
            self.db.update_user(user.id, is_active=1)
            await update.message.reply_text(
                f"{bip_bop()}OK Human! Now everything is ready{bip_bop()}\n"
                f"Use <b>/help</b> if you need some tips!",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Errore durante /start: {e}")
            await self._send_error_message(update)

    async def _handle_new_user(self, update, user: Any) -> None:
        welcome_msg = (
            "Ciao👋! It's your first time😏?"
            f"{bip_bop()}\nWell... Everyone has had a first time😌, "
            "so to start add a new Feeeed in your list with <b>/add</b>\n"
            "If you are lost send me <b>/help</b> then I'll give you some tips😜\n"
            f"{bip_bop()}"
        )
        await update.message.reply_text(welcome_msg, parse_mode="HTML")
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
        query = update.callback_query

        if query != None:
            await query.answer()
            data = query.data

            message, keyboard = feed_message.send_feed(
                telegraph=data["set_telegraph"],
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
        query = update.callback_query
        telegram_user = query.from_user
        if query != None:
            await query.answer()
            data = query.data

            # data è così composto:
            # "alias"
            # "set_telegraph"
            # "url'

            if data["set_telegraph"] == True:
                new_link = "✳️Normal Link✳️"
                old_link = "🤙Telegraph Link🤙"
            else:
                new_link = "🤙Telegraph Link🤙"
                old_link = "✳️Normal Link✳️"

            self.db.update_user_bookmark(
                telegram_user.id,
                url=data["url"],
                alias=data["alias"],
                telegraph=data["set_telegraph"],
            )

            list = ["wonderful\n", "Marvelous\n", "Amazing\n"]
            message = (
                random.choice(list)
                + "I change '"
                + data["alias"]
                + "' to send by default \n<b>"
                + old_link
                + "</b>!!\nIf you want to receive <b>"
                + new_link
                + "</b>instead click the button below!"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙Change to " + new_link + "🔙",
                        callback_data={
                            "option": "change_database",
                            "alias": data["alias"],
                            "url": data["url"],
                            "set_telegraph": not data["set_telegraph"],
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
        # Adds a rss subscription to user

        telegram_user = update.message.from_user
        args = update.message.text.split()
        list = [
            "🍕Best site for cooking Pizza🍕",
            "🍷Best Site for sciacquare una bottiglia di Brunello",
            "🐶BauBau",
            "😏HotSite.com",
            "💩.it",
            "😴generic_news_boooring_site🥱",
            "🎮Games&Caipiroska🍹",
        ]
        if len(args) < 2:
            message = (
                "Oh nono! I could not add the entry😯!\n"
                + bip_bop()
                + "I need <b>at least</b> a valid URL, and, if you want, a custom name.\n"
                + "Try to send a valid URL like this:"
                + "\n\n"
                + "<code>/add https://duccio.me/rss "
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        arg_url = FeedHandler.format_url_string(string=args[1])

        # Check if argument matches url format
        is_parsable = FeedHandler.is_parsable(url=arg_url)
        if is_parsable != True:
            message = (
                bip_bop()
                + "Sorry! It seems like <code>"
                + str(arg_url)
                + "</code> "
                + str(is_parsable)
                + "...😣.\n Have you tried other URLs?\n"
                + "Try to send a valid URL like this:\n"
                + "<code>/add https://duccio.me/rss  \t"
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        # Check if entry does not exists
        entries = self.db.get_urls_for_user(telegram_id=telegram_user.id)

        if any(arg_url.lower() in entry for entry in entries):
            message = (
                "Sorry, "
                + telegram_user.first_name
                + "! I already have that url with stored in your subscriptions😒"
                + "\nAdd a new one like this:\n"
                + "<code>/add https://duccio.me/rss "
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        if len(args) == 2:
            arg_entry = random_emoji() + " " + FeedHandler.get_feed_title(arg_url)
            if arg_entry == False:
                message = (
                    bip_bop()
                    + "mhh... I tried my best for create a title for that url but I can't...\n"
                    + telegram_user.username
                    + "try to resend <code> /add "
                    + args[1]
                    + "</code> and this time add a costum name!"
                    + bip_bop()
                    + "\nLike this: "
                    + "<code>/add https://duccio.me/rss "
                    + random.choice(list)
                    + "</code>"
                )
                await update.message.reply_text(
                    message,
                    parse_mode="HTML",
                )

        elif len(args) >= 3:
            arg_entry = ""
            for i in range(2, len(args)):
                arg_entry += args[i] + " "

        list1 = ["I'm stressed...😣", "I'm bored... 🥱", "I'm in love...🥰"]
        if any(arg_entry in entry for entry in entries):
            message = (
                "🤬<b>NOOOO!\nI ALREADY HAVE AN ENTRY WITH THAT NAME!!"
                + bip_bop()
                + "</b>\n\n...\n\nSorry 😥, "
                + random.choice(list1)
                + "\nTry to send my another feed like this:\n"
                + "<code>/add https://duccio.me/rss "
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        self.db.add_user_bookmark(
            telegram_id=telegram_user.id, url=arg_url.lower(), alias=arg_entry
        )
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔗Change to Telegraph Link🔗",
                    callback_data={
                        "option": "change_database",
                        "alias": arg_entry,
                        "url": arg_url.lower(),
                        "set_telegraph": False,
                    },
                )
            ],
        ]
        message = (
            "WOOW!!🤝"
            + bip_bop()
            + "\nI successfully added ("
            + arg_entry
            + ") to your subscriptions!"
            + bip_bop()
            + "\n👀Look! By default when I found a new post I try to send <b>Normal Link</b>.\n"
            + "If you want to always receive <b>Telegraph Link</b> (to open with <u>Instant View</u>) click the button below"
        )
        await update.message.reply_text(
            text=message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def get_n_feed(self, update, context):

        # invio tanti messaggi quanti specificati in 'data'
        query = update.callback_query

        if query != None:
            await query.answer()
            telegram_user = query.from_user
            data = query.data
            # data è composto da:  "alias", "url", "user", "number_feed"
            entries = FeedHandler.parse_N_entries(data["url"], data["number_feed"])
            for entry in reversed(entries):
                # print(entry)
                # controllo in che modalità vuole il link:

                db_telegraph = self.db.get_user_bookmark(
                    data["user"], alias=data["alias"]
                )

                message, keyboard = feed_message.send_feed(
                    telegraph=db_telegraph[3],
                    alias=data["alias"],
                    post_link=entry.link,
                    post_title=entry.title,
                )

                await self.bot.bot.send_message(
                    text=message,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    chat_id=data["user"],
                    link_preview_options=LinkPreviewOptions(prefer_small_media=True),
                )

    async def get(self, update, context):
        """
        Manually parses an rss feed
        """

        query = update.callback_query

        if query != None:
            await query.answer()
            telegram_user = query.from_user
            data = query.data
            # data è composto da: alias, url, user
            message = (
                bip_bop()
                + " perfect👌\nSelect how many FEEDs you want receive for: \n\n"
                + data["alias"]
                + "\n"
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
                        "ALL",
                        callback_data={
                            "option": "send_feed",
                            "alias": data["alias"],
                            "url": data["url"],
                            "user": data["user"],
                            "number_feed": 0,
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
            telegram_user = update.message.from_user

            entries = self.db.get_urls_for_user(telegram_id=telegram_user.id)

            remove_list_message, remove_list_keyboard = get_list_handler(
                feed_list=entries, telegram_user=telegram_user
            )

            await update.message.reply_text(
                text=remove_list_message,
                parse_mode="HTML",
                reply_markup=remove_list_keyboard,
            )

    async def remove(self, update, context):
        """
        Displays a list of all user subscriptions
        """

        query = update.callback_query

        if query != None:
            await query.answer()
            telegram_user = query.from_user
            data = query.data
            # data è composto da: alias, url, user
            self.db.remove_user_bookmark(telegram_id=telegram_user.id, url=data["url"])

        else:
            telegram_user = update.message.from_user

        entries = self.db.get_urls_for_user(telegram_id=telegram_user.id)

        remove_list_message, remove_list_keyboard = remove_list_handler(
            feed_list=entries, telegram_user=telegram_user
        )

        if query != None:
            await query.edit_message_text(
                text=remove_list_message,
                parse_mode="HTML",
                reply_markup=remove_list_keyboard,
            )

        else:
            await update.message.reply_text(
                text=remove_list_message,
                parse_mode="HTML",
                reply_markup=remove_list_keyboard,
            )

    async def list(self, update, context):
        """
        Displays a list of all user subscriptions
        """

        telegram_user = update.message.from_user
        message = (
            bip_bop()
            + "🤖! Here is a list of all subscriptions <i>I stored for you</i>❤️!\nIf you want to change the default link click the button below!"
            + bip_bop()
        )
        await update.message.reply_text(message, parse_mode="HTML")

        entries = self.db.get_urls_for_user(telegram_id=telegram_user.id)

        for index, entry in enumerate(entries):
            db_telegraph = self.db.get_user_bookmark(telegram_user.id, alias=entry[1])
            list_message, list_keyboard = list_handler(
                db_telegraph[3], alias=entry[1], url=entry[0], index=index
            )

            await update.message.reply_text(
                text=list_message,
                parse_mode="HTML",
                reply_markup=list_keyboard,
            )

    async def help(self, update, context):
        """
        Send a message when the command /help is issued.
        """
        await update.message.reply_text(help_message(), parse_mode="HTML")

    async def stop(self, update, context):
        """
        Stops the bot from working
        """
        await update.message.reply_text(
            stop_handler(telegram_user=update.message.from_user, db=self.db)
        )

    async def about(self, update, context):
        """
        Shows about information
        """
        message = about_message(number=self.db.get_total_users())
        await update.message.reply_text(text=message, parse_mode="HTML")


if __name__ == "__main__":
    Feedergraph(telegram_token=TELEGRAM_TOKEN, update_interval=UPDATE_INTERVAL)
