import asyncio
import logging
import traceback
from typing import Optional, List, Any
from telegram import LinkPreviewOptions
from telegram.error import RetryAfter, TelegramError

# -----
from utils.database import DatabaseHandler
from utils.filters import matches_filter
from utils.make_text import clean_feed_text
from command.admin import is_admin
import command.feed_message as feed_message
from providers import BaseFeedProvider, FeedItem, get_feed_provider

logger = logging.getLogger(__name__)

_RETRY_AFTER_TYPES = (
    (RetryAfter,)
    if isinstance(RetryAfter, type) and issubclass(RetryAfter, BaseException)
    else ()
)
_TELEGRAM_ERROR_TYPES = (
    (TelegramError,)
    if isinstance(TelegramError, type) and issubclass(TelegramError, BaseException)
    else ()
)


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
        """Runs concurrent polling for all feeds with a rate-limiting semaphore"""
        if not self._is_running:
            return
        if getattr(self, "_run_in_progress", False):
            logger.warning("Previous batch run still in progress, skipping this tick")
            return
        self._run_in_progress = True

        try:
            feeds = self.db.get_all_feeds()
            if not feeds:
                return

            # Bounded concurrency limit to avoid network / rate limit spikes
            sem = asyncio.Semaphore(5)

            async def _process_worker(url: str, last_updated, last_title: str, last_entry_id: Optional[str]):
                async with sem:
                    await self._process_single_feed(url, last_updated, last_title, last_entry_id)

            tasks = [
                _process_worker(feed_url, last_updated, last_title, last_entry_id)
                for feed_url, last_updated, last_title, last_entry_id in feeds
            ]
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.update_interval,
                )
            except asyncio.TimeoutError:
                logger.warning("Batch run timed out after %ss, moving to next tick", self.update_interval)

        except Exception as e:
            logger.error(f"Error during batch execution: {e}")
            traceback.print_exc()
        finally:
            self._run_in_progress = False

    async def _process_single_feed(
        self, feed_url: str, last_updated, last_title: str, last_entry_id: Optional[str]
    ) -> None:
        """Processes a single feed and persists progress even if cancelled mid-batch."""
        try:
            entries = await self._safe_fetch_entries(feed_url)
            if not entries:
                return

            recent_ids = set(self.db.get_recent_entry_ids(feed_url, limit=50))
            if last_entry_id and not recent_ids:
                recent_ids.add(str(last_entry_id))

            new_entries = self._filter_new_entries(entries, recent_ids, last_entry_id)

            if not new_entries:
                return

            delivered_entries: List[FeedItem] = []
            sent = 0
            failed = 0
            filtered = 0
            try:
                sent, failed, filtered = await self._notify_users(
                    feed_url, new_entries, delivered_entries
                )
            finally:
                if delivered_entries:
                    latest_delivered = delivered_entries[-1]
                    self._update_feed_metadata(feed_url, latest_delivered)

                    if len(delivered_entries) == len(new_entries):
                        recorded_ids = [str(e.id) for e in entries[:50]]
                    else:
                        recorded_ids = [str(e.id) for e in delivered_entries]
                    self.db.record_feed_entries(feed_url, recorded_ids, max_keep=50)
                elif sent == 0 and failed > 0 and filtered == 0:
                    logger.warning(
                        "All %d sends failed for %s, keeping cursor for retry",
                        failed,
                        feed_url,
                    )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {e}")
            traceback.print_exc()

    def _filter_new_entries(
        self,
        entries: List[FeedItem],
        known_entry_ids: Optional[Any] = None,
        last_entry_id: Optional[str] = None,
    ) -> List[FeedItem]:
        """
        Filters unread articles based on known entry IDs window (up to 50 items) or last_entry_id.
        """
        if isinstance(known_entry_ids, str):
            known_ids_set = {known_entry_ids} if known_entry_ids else set()
        elif isinstance(known_entry_ids, (set, list)):
            known_ids_set = {str(eid) for eid in known_entry_ids if str(eid)}
        else:
            known_ids_set = set()

        if last_entry_id:
            known_ids_set.add(str(last_entry_id))

        if not known_ids_set:
            # First run or no history saved: return all available articles
            return entries

        new_items: List[FeedItem] = []
        for entry in entries:
            if str(entry.id) not in known_ids_set:
                new_items.append(entry)
            else:
                break

        return new_items

    async def _safe_fetch_entries(self, feed_url: str) -> Optional[List[FeedItem]]:
        """Fetches entries with error handling via the feed provider"""
        try:
            return await asyncio.to_thread(self.provider.fetch_entries, feed_url, 0)
        except Exception as e:
            logger.warning(f"Error fetching entries for {feed_url}: {e}")
            return None

    async def _notify_users(
        self,
        feed_url: str,
        entries: List[FeedItem],
        delivered_entries: Optional[List[FeedItem]] = None,
    ) -> tuple:
        """Notifies subscribed users with their alias and preference.

        Returns (sent, failed, filtered) counts so the caller can decide
        whether to advance the feed cursor.
        """
        users = self.db.get_active_users_for_feed(feed_url)
        if not users:
            return 0, 0, 0

        logger.info(f"Sending {len(entries)} new entries to {len(users)} users for {feed_url}")

        sent = 0
        failed = 0
        filtered = 0
        for entry in reversed(entries):
            entry_sent = 0
            entry_failed = 0
            entry_filtered = 0

            for user_id, prefers_telegraph, user_alias, filter_rules in users:
                if filter_rules and not matches_filter(entry, filter_rules):
                    filtered += 1
                    entry_filtered += 1
                    logger.info(
                        "Skipped entry %s for user %s due to filter rules",
                        entry.id,
                        user_id,
                    )
                    continue

                # Only admins can use automatic per-feed Telegraph conversion;
                # normal users receive the normal link and can convert on-demand via button.
                effective_telegraph = bool(prefers_telegraph) and is_admin(user_id)

                try:
                    res = await self._send_entry_to_user(
                        user_id=user_id,
                        entry=entry,
                        alias=user_alias,
                        use_telegraph=effective_telegraph,
                    )
                    if res is False:
                        failed += 1
                        entry_failed += 1
                    else:
                        sent += 1
                        entry_sent += 1
                        # 1.0 second delay between messages to prevent Telegram rate limits
                        await asyncio.sleep(1.0)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    failed += 1
                    entry_failed += 1
                    logger.error(f"Error sending entry {entry.id} to {user_id}: {e}")
                    traceback.print_exc()

            if delivered_entries is not None and (
                entry_sent > 0 or (entry_failed == 0 and entry_filtered > 0)
            ):
                delivered_entries.append(entry)

        if filtered or failed:
            logger.info(
                "Feed %s: sent %d/%d (filtered %d, failed %d)",
                feed_url,
                sent,
                len(entries) * len(users),
                filtered,
                failed,
            )
        return sent, failed, filtered

    async def _send_entry_to_user(
        self, user_id: int, entry: FeedItem, alias: str, use_telegraph: bool
    ) -> bool:
        """Sends a single entry to a user. Returns True if delivered (or user deactivated), False if failed."""
        post_link = entry.source_link or entry.link
        post_title = entry.title or "No Title"

        if use_telegraph:
            try:
                message, keyboard = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: feed_message.send_feed(
                            telegraph=True,
                            alias=alias,
                            post_link=post_link,
                            post_title=post_title,
                            tags=entry.tags,
                            summary=entry.summary or "",
                        )
                    ),
                    timeout=45,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Message build timed out for entry {entry.id}, using original link")
                message, keyboard = feed_message.send_feed(
                    telegraph=False,
                    alias=alias,
                    post_link=post_link,
                    post_title=post_title,
                    tags=entry.tags,
                    summary=entry.summary or "",
                )
        else:
            message, keyboard = feed_message.send_feed(
                telegraph=False,
                alias=alias,
                post_link=post_link,
                post_title=post_title,
                tags=entry.tags,
                summary=entry.summary or "",
            )

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                await self.bot.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    link_preview_options=LinkPreviewOptions(prefer_small_media=True),
                )
                return True
            except _RETRY_AFTER_TYPES as e:
                retry_secs = getattr(e, "retry_after", 5)
                logger.warning(f"Rate limit for {user_id}: waiting {retry_secs}s")
                await asyncio.sleep(retry_secs)
            except _TELEGRAM_ERROR_TYPES as e:
                err_msg = str(e).lower()
                if any(
                    perm_err in err_msg
                    for perm_err in (
                        "chat not found",
                        "bot was blocked",
                        "user is deactivated",
                        "chat_write_forbidden",
                        "have no rights to send a message",
                    )
                ):
                    logger.info(f"Deactivating user {user_id} due to permanent error: {e}")
                    self.db.deactivate_user(user_id)
                    return True

                if attempt < max_attempts and any(
                    trans in err_msg
                    for trans in ("timed out", "timeout", "network", "connection", "bad gateway", "gateway timeout")
                ):
                    logger.warning(
                        f"Transient Telegram error for {user_id} (attempt {attempt}/{max_attempts}): {e}"
                    )
                    await asyncio.sleep(1.5 * attempt)
                    continue

                logger.error(f"Non-fatal Telegram error for {user_id}: {e}")
                return False

        return False

    def _update_feed_metadata(self, feed_url: str, latest_entry: FeedItem) -> None:
        """Updates feed metadata, including latest entry ID."""
        self.db.update_feed(
            url=feed_url,
            last_updated=str(latest_entry.published) if latest_entry.published else None,
            last_title=clean_feed_text(latest_entry.title) or "No Title",
            last_entry_id=str(latest_entry.id),
        )

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        self._is_running = value
