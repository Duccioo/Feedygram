# /bin/bash/python
# encoding: utf-8


from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import os
from dotenv import load_dotenv
import random

# -----
from utils.database import DatabaseHandler
from utils.feedhandler import FeedHandler
from utils.make_text import bip_bop, random_emoji, number_to_emoji
from command.processing import BatchProcess
from command.other_commands import (
    list_handler,
    stop_handler,
    help_message,
    about_message,
)
import command.feed_message as feed_message
from command.important_command import remove_list_handler, get_list_handler


load_dotenv()
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
UPDATE_INTERVAL = os.environ["UPDATE_INTERVAL"]


def check_change_feed_link(obj):
    try:
        if obj["option"] == "change_feed_link":
            return True
        else:
            return False
    except:
        return False


def check_send_feed(obj):
    try:
        if obj["option"] == "send_feed":
            return True
        else:
            return False
    except:
        return False


def check_how_many_feed(obj):
    try:
        if obj["option"] == "select_how_many_feed":
            return True
        else:
            return False
    except:
        return False


def check_change_link(obj):
    try:
        if obj["option"] == "change_database":
            return True
        else:
            return False
    except:
        return False


def check_remove_feed(obj):
    try:
        if obj["option"] == "delete_feed":
            return True
        else:
            return False
    except:

        return False


class Feedergraph(object):
    def __init__(self, telegram_token, update_interval):

        # Initialize bot internals
        self.db = DatabaseHandler("database", "data", "datastore.db")

        self.bot = (
            Application.builder()
            .token(telegram_token)
            .concurrent_updates(True)
            .arbitrary_callback_data(True)
            .build()
        )
        self.job_queue = self.bot.job_queue

        # Add Commands to bot
        self._addCommand(CommandHandler("start", self.start))
        self._addCommand(CommandHandler("stop", self.stop))
        self._addCommand(CommandHandler("help", self.help))
        self._addCommand(CommandHandler("list", self.list))
        self._addCommand(CommandHandler("about", self.about))
        self._addCommand(CommandHandler("add", self.add))
        self._addCommand(CommandHandler("get", self.get))
        self._addCommand(CommandHandler("remove", self.remove))

        self.bot.add_handler(
            CallbackQueryHandler(self.change_list_type, pattern=check_change_link)
        )

        self.bot.add_handler(
            CallbackQueryHandler(self.remove, pattern=check_remove_feed)
        )

        self.bot.add_handler(
            CallbackQueryHandler(self.get, pattern=check_how_many_feed)
        )
        self.bot.add_handler(
            CallbackQueryHandler(self.get_n_feed, pattern=check_send_feed)
        )

        self.bot.add_handler(
            CallbackQueryHandler(self.update_message, pattern=check_change_feed_link)
        )

        # Start the Bot
        self.processing = BatchProcess(
            database=self.db, update_interval=update_interval, bot=self.bot
        )

        self.job_queue.run_repeating(self.processing.run, int(update_interval), first=1)
        self.bot.run_polling()

    def _addCommand(self, command):
        """
        Registers a new command to the bot
        """
        self.bot.add_handler(command)

    async def start(self, update, context: ContextTypes.DEFAULT_TYPE):
        """
        Send a message when the command /start is issued.
        """
        telegram_user = update.message.from_user

        # Add new User if not exists
        if not self.db.get_user(telegram_id=telegram_user.id):

            message = (
                "Ciao👋! It's your first time😏?"
                + bip_bop()
                + "\nWell... Everyone has had a first time😌, so to start add a new Feeeed in your list with <b>/add</b>\n"
                + "If you are lost send me <b>/help</b> then Then I'll give you some tips😜\n"
                + bip_bop()
            )
            await update.message.reply_text(message, parse_mode="HTML")

            # Aggiungo utente al database
            self.db.add_user(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                firstname=telegram_user.first_name,
                lastname=telegram_user.last_name,
                language_code=telegram_user.language_code,
                is_bot=telegram_user.is_bot,
                is_active=1,
            )

        # altrimenti se ho già segnato l'utente lo attivo (in caso fosse inattivo)
        self.db.update_user(telegram_id=telegram_user.id, is_active=1)

        message = (
            bip_bop()
            + "OK Human! Now everything is ready"
            + bip_bop()
            + "\nUse <b>/help</b> if you need some tips!"
        )
        await update.message.reply_text(message, parse_mode="HTML")

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
                + "<code>/add https://duccio.me/ "
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
                + "<code>/add https://duccio.me/ "
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
                + "!I already have that url with stored in your subscriptions😒"
                + "\nAdd a new one like this:\n"
                + "<code>/add https://duccio.me/ "
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
                    + "<code>/add https://duccio.me/ "
                    + random.choice(list)
                    + "</code>"
                )
                await update.message.reply_text(
                    message,
                    parse_mode="HTML",
                )

        elif len(args) >= 3:
            arg_entry = ""
            for i in range(3, len(args)):
                arg_entry = arg_entry + " " + args[i]
        list1 = ["I'm stressed...😣", "I'm bored... 🥱", "I'm in love...🥰"]
        if any(arg_entry in entry for entry in entries):
            message = (
                "🤬<b>NOOOO!\nI ALREADY HAVE AN ENTRY WITH THAT NAMEEE!!"
                + bip_bop()
                + "</b>\n\n...\n\nSorry 😥, "
                + random.choice(list1)
                + "\nTry to send my another feed like this:\n"
                + "<code>/add https://duccio.me/ "
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
        message = about_message(number=self.db.get_total_user())
        await update.message.reply_text(text=message, parse_mode="HTML")


if __name__ == "__main__":
    Feedergraph(telegram_token=TELEGRAM_TOKEN, update_interval=UPDATE_INTERVAL)
