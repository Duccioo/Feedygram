# /bin/bash/python
# encoding: utf-8

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.filehandler import FileHandler
from utils.database import DatabaseHandler
from command.processing import BatchProcess
from utils.feedhandler import FeedHandler
import os
from dotenv import load_dotenv

import webpage2telegraph
import random
from utils.make_text import bip_bop, random_emoji, number_to_emoji
from command.other_commands import (
    list_handler,
    stop_handler,
    help_message,
    about_message,
)


load_dotenv()


TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

UPDATE_INTERVAL = os.environ["UPDATE_INTERVAL"]


def check_change_link(obj):
    try:
        if obj["option"] == "change_database":
            return True
    except:
        return False


class Feedergraph(object):
    def __init__(self, telegram_token, update_interval):

        # Initialize bot internals
        self.db = DatabaseHandler("database/datastore.db")
        self.fh = FileHandler("database/setub.sql")

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
            CallbackQueryHandler(self.change_link_type, pattern=check_change_link)
        )

        self.bot.add_handler(CallbackQueryHandler(self.update_message))

        # Start the Bot
        self.processing = BatchProcess(
            database=self.db, update_interval=update_interval, bot=self.bot
        )

        self.job_queue.run_repeating(self.processing.run, update_interval, first=1)

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

    async def change_link_type(self, update, context):
        query = update.callback_query
        telegram_user = query.from_user
        if query != None:
            await query.answer()
            data = query.data

            # mi vado a prendere nel database se i link sono in versione telegraph
            db_telegraph = self.db.get_user_bookmark(
                telegram_user.id, alias=data["alias"]
            )

            if db_telegraph != None:
                self.db.update_user_bookmark(
                    telegram_user.id,
                    url=data["url"],
                    alias=data["alias"],
                    telegraph=not db_telegraph[3],
                )

                if db_telegraph[3]:
                    new_link = "Normal Link"
                    old_link = "Telegraph Link"
                else:
                    new_link = "Telegraph Link"
                    old_link = "Normal Link"
                list = ["wonderful", "Marvelous"]
                message = (
                    random.choice(list)
                    + "I change '"
                    + data["alias"]
                    + "' to send by default <b>"
                    + new_link
                    + "</b>!!\nIf you want to receive <b>"
                    + old_link
                    + "</b> click the button below!"
                )

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔙Change to " + old_link + "🔙",
                            callback_data={
                                "option": "change_database",
                                "alias": data["alias"],
                                "url": data["url"],
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
        print(arg_url)
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
            arg_entry = (
                random_emoji()
                + " "
                + FeedHandler.get_feed_title(arg_url)
                + " "
                + random_emoji()
            )
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
                    },
                )
            ],
        ]
        message = (
            "WOOW!!🤝"
            + bip_bop()
            + "\nI successfully added "
            + arg_entry
            + " to your subscriptions!"
            + bip_bop()
            + "\n👀Look! By default when I found a new post I try to send <b>Normal Link</b>.\n"
            + "If you want to always receive <b>Telegraph Link</b> (to open with <u>Instant View</u>) click the button below"
        )
        await update.message.reply_text(
            text=message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def get(self, update, context):
        """
        Manually parses an rss feed
        """

        telegram_user = update.message.from_user
        args = update.message.text.split()

        if len(args) > 3 or len(args) <= 1:
            message = "To get the last news of your subscription please use /get <entryname> [optional: <count 1-10>]. Make sure you first add a feed using the /add command."
            await update.message.reply_text(message)
            return

        if len(args) == 3:
            args_entry = args[1].lower()
            args_count = int(args[2])
        else:
            args_entry = args[1]
            args_count = 1

        url = self.db.get_user_bookmark(telegram_id=telegram_user.id, alias=args_entry)

        if url is None:
            message = (
                "I can not find an entry with label "
                + args_entry
                + " in your subscriptions! Please check your subscriptions using /list and use the delete command again!"
            )
            await update.message.reply_text(message)
            return

        entries = FeedHandler.parse_feed(url[0], args_count)
        for entry in entries.entries[:args_count]:
            message = (
                "["
                + url[1]
                + "] <a href='"
                + entry.link
                + "'>"
                + entry.title
                + str(entries.feed.updated)
                + "</a>"
            )

            try:
                await update.message.reply_text(message, parse_mode="HTML")

            except:
                print("errore")
                # handle all other telegram related errors
                pass

    async def remove(self, update, context):
        """
        Removes an rss subscription from user
        """

        args = context.args

        telegram_user = update.message.from_user

        if len(args) < 1:
            message = "To remove a subscriptions from your list please use /remove <entryname>. To see all your subscriptions along with their entry names use /list !"
            await update.message.reply_text(message)
            return

        entry_args = (" ").join(args[0:])
        print(entry_args)

        entry = self.db.get_user_bookmark(
            telegram_id=telegram_user.id, alias=entry_args
        )

        if entry:
            self.db.remove_user_bookmark(telegram_id=telegram_user.id, url=entry[0])
            message = (
                "Mhh..."
                + bip_bop()
                + "OK, I removed "
                + entry_args
                + " from your subscriptions!"
            )
            await update.message.reply_text(message)
        else:
            message = (
                "I can not find an entry with label "
                + args[0]
                + " in your subscriptions! Please check your subscriptions using /list and use the delete command again!"
            )
            await update.message.reply_text(message)

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
        await update.message.reply_text(about_message(db=self.db), parse_mode="HTML")


if __name__ == "__main__":
    Feedergraph(telegram_token=TELEGRAM_TOKEN, update_interval=UPDATE_INTERVAL)
