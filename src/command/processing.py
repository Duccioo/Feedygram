# /bin/bash/python/
from telegram.error import TelegramError
import traceback

# -----
from utils.datehandler import DateHandler
from utils.feedhandler import FeedHandler
import command.feed_message as feed_message


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

        # mi prendo tutti gli utenti che hanno quel particolare url salvato
        telegram_users = self.db.get_users_for_url(url=url[0])

        # istanzio la variabile per aggiornare la data
        update_date = False

        for user in telegram_users:
            if user[6]:  # is_active

                try:

                    feed = FeedHandler.parse_N_entries(url[0])

                    for post in reversed(feed):
                        print("          ", post.title)

                        post_update_date = DateHandler.parse_datetime(
                            datetime=post.updated
                        )
                        url_update_date = DateHandler.parse_datetime(datetime=url[1])

                        if post_update_date > url_update_date:
                            print("!!!!nuovo post trovato!!!!")
                            update_date = True

                            message, reply_markup = feed_message.send_feed(
                                user[8], user[7], post.link, post.title
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

        if update_date == True:
            print("aggiorno la data perchè ho trovato un nuovo articolo")
            self.db.update_url(
                url=url[0],
                last_updated=DateHandler.parse_datetime(
                    datetime=FeedHandler.parse_first_entries(url[0]).updated
                ),
                last_title=str(
                    (FeedHandler.parse_first_entries(url[0])).title.replace('"', "'")
                ),
            )

    def set_running(self, running):
        self.running = running
