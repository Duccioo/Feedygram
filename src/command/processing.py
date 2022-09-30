# /bin/bash/python/


from telegram.error import TelegramError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from utils.datehandler import DateHandler
from utils.feedhandler import FeedHandler
import traceback
import webpage2telegraph
import random


# class BatchProcess(threading.Thread):
class BatchProcess:
    def __init__(self, database, update_interval, bot):
        # RunningThread.__init__(self)
        self.db = database
        self.update_interval = float(update_interval)
        self.bot = bot
        self.running = True

    async def run(self, context):
        """
        Start refreshing url
        """
        url_queue = self.db.get_all_urls()
        for item in url_queue:
            await self.update_feed(item)

    async def update_feed(self, url):
        print(url)

        telegram_users = self.db.get_users_for_url(url=url[0])

        for user in telegram_users:
            if user[6]:  # is_active
                try:
                    feed = FeedHandler.parse_N_entries(url[0], 2)
                    for post in feed:
                        await self.send_newest_messages(
                            url=url, feed=feed, user=user, post=post
                        )

                except:
                    traceback.print_exc()
                    message = (
                        "Something went wrong when I tried to parse the URL: \n\n "
                        + url[0]
                        + "\n\nCould you please check that for me? Remove the url from your subscriptions using the /remove command, it seems like it does not work anymore!"
                    )

                    await self.bot.bot.send_message(
                        chat_id=user[0],
                        text=message,
                        parse_mode="HTML",
                    )

        self.db.update_url(
            url=url[0],
            last_updated=str(DateHandler.get_datetime_now()),
            last_title=str((FeedHandler.parse_first_entries(url[0])).title),
        )

    async def send_newest_messages(self, url, post, user, feed):

        keyboard_telegraph = [
            [
                InlineKeyboardButton(
                    "🤙Telegraph Link🤙",
                    callback_data={
                        "alias": user[7],
                        "set_telegraph": True,
                        "link": post.link,
                        "title": post.title,
                    },
                ),
            ],
        ]

        keyboard_normal = [
            [
                InlineKeyboardButton(
                    "✳️Normal Link✳️",
                    callback_data={
                        "alias": user[7],
                        "set_telegraph": False,
                        "link": post.link,
                        "title": post.title,
                    },
                )
            ],
        ]

        set_telegraph = user[8]
        post_update_date = DateHandler.parse_datetime(datetime=post.updated)
        url_update_date = DateHandler.parse_datetime(datetime=url[1])

        if post_update_date > url_update_date:
            if set_telegraph:
                reply_markup = InlineKeyboardMarkup(keyboard_normal)
                title_first = post.title
                link_first = str(webpage2telegraph.transfer(post.link))
                title_second = "Normal Link"
                link_second = post.link
            else:
                reply_markup = InlineKeyboardMarkup(keyboard_telegraph)
                title_first = post.title
                link_first = post.link
                title_second = "Telegraph Link"
                link_second = str(webpage2telegraph.transfer(post.link))

            list = [
                "New Update! ",
                "Something Change in ",
                "Here's for you, from",
                "Drin drin! ",
                "News FROM ",
            ]

            message = (
                "🔔"
                + random.choice(list)
                + "["
                + user[7]
                + "] \n--------------------------------------------------\n <a href='"
                + link_first
                + "'>"
                + title_first
                + "</a>"
                + "\n--------------------------------------------------\n<a href='"
                + link_second
                + "'>"
                + "["
                + title_second
                + "]"
                + "</a>"
            )

            try:
                await self.bot.bot.send_message(
                    chat_id=user[0],
                    text=message,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )

            except TelegramError:
                print(TelegramError)
                # handle all other telegram related errors
                pass

    def set_running(self, running):
        self.running = running
