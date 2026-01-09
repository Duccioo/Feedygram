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
            for feed_url, last_updated, last_title, last_entry_id, alias in feeds:
                await self._process_single_feed(feed_url, last_updated, last_title, last_entry_id, alias)

        except Exception as e:
            print(f"Errore durante l'esecuzione del batch: {e}")
            # Implementare logica di ripristino se necessario

    async def _process_single_feed(self, feed_url: str, last_updated, last_title: str, last_entry_id: str, alias: str) -> None:
        """Elabora un singolo feed"""
        try:
            entries = await self._safe_fetch_entries(feed_url)
            if not entries:
                return

            new_entries = self._filter_new_entries(entries, last_entry_id)

            if not new_entries:
                return

            await self._notify_users(feed_url, new_entries, alias)
            latest_entry = new_entries[0]
            self._update_feed_metadata(feed_url, latest_entry)

        except Exception as e:
            print(f"Errore durante l'elaborazione del feed {feed_url}: {e}")
            traceback.print_exc()

    def _filter_new_entries(self, entries, last_entry_id: str):
        """
        Filtra gli articoli non ancora elaborati basandosi sull'ID univoco (guid).
        """
        if not last_entry_id:
            # Se non abbiamo un ID di riferimento, consideriamo solo l'articolo più recente per evitare di inviare l'intero feed
            return entries[:1]

        try:
            # Trova l'indice dell'ultimo articolo che abbiamo inviato
            last_index = next(i for i, entry in enumerate(entries) if hasattr(entry, 'id') and entry.id == last_entry_id)
            # Restituisce tutti gli articoli più recenti di quello
            return entries[:last_index]
        except StopIteration:
            # Se il vecchio ID non è più nel feed, inviamo solo l'articolo più recente per sicurezza
            return entries[:1]

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

        # Try to extract a direct source link to avoid proxy/preview issues
        source_link = FeedHandler.extract_source_link(entry)
        safe_link = html.escape(source_link if source_link else entry.link)

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
        """Aggiorna i metadati del feed, incluso l'ID dell'ultimo entry."""
        new_last_entry_id = getattr(latest_entry, 'id', None)
        if not new_last_entry_id:
            print(f"Attenzione: ID non trovato per l'ultimo entry del feed {feed_url}. La deduplicazione potrebbe non funzionare.")
            # Fallback a un valore non nullo per evitare di riprocessare all'infinito
            new_last_entry_id = latest_entry.link

        self.db.update_feed(
            url=feed_url,
            last_updated=DateHandler.parse_datetime(latest_entry.updated),
            last_title=html.escape(latest_entry.title),
            last_entry_id=new_last_entry_id
        )

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        self._is_running = value
