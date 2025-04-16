# /bin/bash/python/
from telegram.error import RetryAfter, TelegramError
import traceback
import html
from telegram import LinkPreviewOptions

# -----
from utils.datehandler import DateHandler
from utils.feedhandler import FeedHandler
import command.feed_message as feed_message
from utils.database import DatabaseHandler


class BatchProcess:
    def __init__(self, database: DatabaseHandler, update_interval: float, bot):
        self.db: DatabaseHandler = database
        self.update_interval = float(update_interval)
        self.bot = bot
        self._is_running = True
        self.cache = {}

    async def run(self, context) -> None:
        """Esegue il polling periodico di tutti i feed"""
        if not self._is_running:
            return

        try:
            feeds = self.db.get_all_feeds()
            for feed_url, last_updated, last_title, alias in feeds:
                await self._process_single_feed(feed_url, last_updated, last_title, alias)

        except Exception as e:
            print(f"\nErrore durante l'esecuzione del batch: {e}")
            # Implementare logica di ripristino se necessario

    async def _process_single_feed(self, feed_url: str, last_updated, last_title: str, alias: str) -> None:
        """Elabora un singolo feed"""
        try:

            entries = await self._safe_fetch_entries(feed_url)
            if entries is None:
                return

            new_entries = self._filter_new_entries(feed_url, entries, last_updated, last_title)

            if not new_entries:
                return

            await self._notify_users(feed_url, new_entries, alias)
            self._update_feed_metadata(feed_url, new_entries[0])

        except Exception as e:
            print(f"Errore elaborazione feed {feed_url}: {e}")

    def _filter_new_entries(self, feed_url, entries, last_updated, last_title):
        """Filtra solo i nuovi entry"""

        if feed_url not in self.cache:
            self.cache[feed_url] = {"last_title": last_title, "flag": 0}

        new_entries = []
        for entry in entries:
            if entry.title != last_title:
                if DateHandler.parse_datetime(entry.updated) > DateHandler.parse_datetime(last_updated):
                    new_entries.append(entry)
                    self.cache[feed_url] = {"last_title": entry.title, "flag": 0}

            elif self.cache[feed_url]["flag"] < 2:
                if DateHandler.parse_datetime(entry.updated) > DateHandler.parse_datetime(last_updated):
                    new_entries.append(entry)
                    self.cache[feed_url]["flag"] += 1

        # new_entries = [
        #     entry
        #     for entry in entries
        #     if entry.title != last_title
        #     and DateHandler.parse_datetime(entry.updated)
        #     > DateHandler.parse_datetime(last_updated)
        # ]

        # Ordina i nuovi entry per data di pubblicazione (in modo decrescente)
        new_entries.sort(key=lambda x: x.updated, reverse=True)

        return new_entries

    async def _safe_fetch_entries(self, feed_url: str):
        """Fetch degli entry con gestione errori"""
        try:
            return FeedHandler.parse_N_entries(feed_url, -1)
        except Exception as e:
            return None

    async def _notify_users(self, feed_url: str, entries, alias: str) -> None:
        """Notifica gli utenti iscritti"""
        users = self.db.get_active_users_for_feed(feed_url)
        if not users:
            return

        print(f"Invio {len(entries)} nuovi entry a {len(users)} utenti per {feed_url}")

        for entry in reversed(entries):
            for user_id, prefers_telegraph in users:
                try:
                    await self._send_entry_to_user(
                        user_id=user_id,
                        entry=entry,
                        alias=alias,
                        use_telegraph=prefers_telegraph,
                    )
                except Exception as e:
                    print(f"Errore invio a {user_id}: {e}")
                    traceback.print_exc()
                    message = (
                        "Something went wrong when I tried to parse the URL: \n\n "
                        + feed_url
                        + "\n\nCould you please check that for me? Remove the url from your subscriptions using the /remove command, it seems like it does not work anymore!"
                    )
                    await self.bot.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode="HTML",
                    )

    async def _send_entry_to_user(self, user_id: int, entry, alias: str, use_telegraph: bool) -> None:
        """Invia un singolo entry a un utente"""
        safe_title = html.escape(entry.title)
        safe_link = html.escape(entry.link)

        message, keyboard = feed_message.send_feed(
            telegraph=use_telegraph,
            alias=alias,
            post_link=safe_link,
            post_title=safe_title,
        )

        try:
            await self.bot.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                link_preview_options=LinkPreviewOptions(prefer_small_media=True),
            )
        except RetryAfter as e:
            print(f"Rate limit per {user_id}: {e}")
            # await asyncio.sleep(e.retry_after)
            await self._send_entry_to_user(user_id, entry, alias, use_telegraph)
        except TelegramError as e:
            if "chat not found" in str(e).lower():
                print(f"Disattivazione utente {user_id}")
                self.db.deactivate_user(user_id)

    def _update_feed_metadata(self, feed_url: str, latest_entry) -> None:
        """Aggiorna i metadati del feed"""
        self.db.update_feed(
            url=feed_url,
            last_updated=DateHandler.parse_datetime(latest_entry.updated),
            last_title=html.escape(latest_entry.title),
        )

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        self._is_running = value
