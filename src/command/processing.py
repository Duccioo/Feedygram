import asyncio
import logging
import traceback
from typing import Optional, List
from telegram import LinkPreviewOptions
from telegram.error import RetryAfter, TelegramError

# -----
from utils.database import DatabaseHandler
from utils.filters import matches_filter
import command.feed_message as feed_message
from providers import BaseFeedProvider, FeedItem, get_feed_provider

logger = logging.getLogger(__name__)


class BatchProcess:
    def __init__(
        self,
        database: DatabaseHandler,
        update_interval: float,
        bot,
        provider: Optional[BaseFeedProvider] = None,
    ):
        self.db: DatabaseHandler = database
        self.update_interval = float(update_interval)
        self.bot = bot
        self.provider: BaseFeedProvider = provider or get_feed_provider()
        self._is_running = True

    async def run(self, context=None) -> None:
        """Esegue il polling concorrente di tutti i feed con un semaforo limitatore"""
        if not self._is_running:
            return

        try:
            feeds = self.db.get_all_feeds()
            if not feeds:
                return

            # ponytail: bounded concurrency limit to avoid network / rate limit spikes
            sem = asyncio.Semaphore(5)

            async def _process_worker(url: str, last_updated, last_title: str, last_entry_id: Optional[str]):
                async with sem:
                    await self._process_single_feed(url, last_updated, last_title, last_entry_id)

            tasks = [
                _process_worker(feed_url, last_updated, last_title, last_entry_id)
                for feed_url, last_updated, last_title, last_entry_id in feeds
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Errore durante l'esecuzione del batch: {e}")
            traceback.print_exc()

    async def _process_single_feed(
        self, feed_url: str, last_updated, last_title: str, last_entry_id: Optional[str]
    ) -> None:
        """Elabora un singolo feed"""
        try:
            entries = await self._safe_fetch_entries(feed_url)
            if not entries:
                return

            new_entries = self._filter_new_entries(entries, last_entry_id)

            if not new_entries:
                return

            await self._notify_users(feed_url, new_entries)
            latest_entry = new_entries[0]
            self._update_feed_metadata(feed_url, latest_entry)

        except Exception as e:
            logger.error(f"Errore durante l'elaborazione del feed {feed_url}: {e}")
            traceback.print_exc()

    def _filter_new_entries(self, entries: List[FeedItem], last_entry_id: Optional[str]) -> List[FeedItem]:
        """
        Filtra gli articoli non ancora elaborati basandosi sull'ID univoco calcolato.
        """
        if not last_entry_id:
            # Primo avvio o nessun ID salvato: consideriamo solo l'articolo più recente per evitare flood
            return entries[:1]

        for i, entry in enumerate(entries):
            if str(entry.id) == str(last_entry_id):
                # Restituisce tutti gli articoli più recenti di quello già elaborato
                return entries[:i]

        # Se il vecchio ID non è più presente nella finestra del feed, prendiamo solo l'articolo più recente
        return entries[:1]

    async def _safe_fetch_entries(self, feed_url: str) -> Optional[List[FeedItem]]:
        """Fetch degli entry con gestione errori tramite il feed provider"""
        try:
            return self.provider.fetch_entries(feed_url, limit=0)
        except Exception as e:
            logger.warning(f"Errore fetch entries per {feed_url}: {e}")
            return None

    async def _notify_users(self, feed_url: str, entries: List[FeedItem]) -> None:
        """Notifica gli utenti iscritti con il loro alias e preferenza"""
        users = self.db.get_active_users_for_feed(feed_url)
        if not users:
            return

        logger.info(f"Invio {len(entries)} nuovi entry a {len(users)} utenti per {feed_url}")

        for entry in reversed(entries):
            for user_id, prefers_telegraph, user_alias, filter_rules in users:
                if filter_rules and not matches_filter(entry, filter_rules):
                    continue
                try:
                    await self._send_entry_to_user(
                        user_id=user_id,
                        entry=entry,
                        alias=user_alias,
                        use_telegraph=prefers_telegraph,
                    )
                except Exception as e:
                    logger.error(f"Errore invio a {user_id}: {e}")
                    traceback.print_exc()

    async def _send_entry_to_user(
        self, user_id: int, entry: FeedItem, alias: str, use_telegraph: bool
    ) -> None:
        """Invia un singolo entry a un utente"""
        post_link = entry.source_link or entry.link
        post_title = entry.title or "No Title"

        message, keyboard = feed_message.send_feed(
            telegraph=use_telegraph,
            alias=alias,
            post_link=post_link,
            post_title=post_title,
            tags=entry.tags,
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
            logger.warning(f"Rate limit per {user_id}: attesa {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await self.bot.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                link_preview_options=LinkPreviewOptions(prefer_small_media=True),
            )
        except TelegramError as e:
            err_msg = str(e).lower()
            if "chat not found" in err_msg or "bot was blocked" in err_msg or "user is deactivated" in err_msg:
                logger.info(f"Disattivazione utente {user_id} per errore: {e}")
                self.db.deactivate_user(user_id)
            else:
                logger.error(f"Errore Telegram non fatale per {user_id}: {e}")

    def _update_feed_metadata(self, feed_url: str, latest_entry: FeedItem) -> None:
        """Aggiorna i metadati del feed, incluso l'ID univoco dell'ultimo entry."""
        self.db.update_feed(
            url=feed_url,
            last_updated=str(latest_entry.published) if latest_entry.published else None,
            last_title=latest_entry.title or "No Title",
            last_entry_id=str(latest_entry.id),
        )

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        self._is_running = value


