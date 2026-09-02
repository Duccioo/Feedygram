import sqlite3
import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple, Any
from urllib.parse import urlparse
from datetime import datetime
from contextlib import contextmanager

# ---
from utils.datehandler import DateHandler as dh

# Logging configuration
logger = logging.getLogger(__name__)


class DatabaseHandler:
    def __init__(self, *database_path: str):
        base_dir = Path(__file__).resolve().parent.parent
        self.database_path = str(base_dir.joinpath(*database_path))
        logger.info("Database path: %s", self.database_path)

        self._init_database()
        self._enable_foreign_keys()

    def _init_database(self) -> None:
        """Initializes database if missing and executes necessary migrations"""
        db_dir = os.path.dirname(self.database_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        if not os.path.exists(self.database_path):
            logger.info("Creating new database: %s", self.database_path)
            self._execute_schema_script()
        else:
            self._run_migrations()

    def _run_migrations(self) -> None:
        """Applies schema migrations for existing databases"""
        try:
            with self._get_connection() as conn:
                # web_user migration (filter_rules)
                cursor = conn.execute("PRAGMA table_info(web_user)")
                columns_wu = [row[1] for row in cursor.fetchall()]
                if "filter_rules" not in columns_wu:
                    conn.execute("ALTER TABLE web_user ADD COLUMN filter_rules TEXT DEFAULT ''")
                    logger.info("Added filter_rules column to web_user")

                # web migration (last_entry_id)
                cursor = conn.execute("PRAGMA table_info(web)")
                columns_w = [row[1] for row in cursor.fetchall()]
                if "last_entry_id" not in columns_w:
                    conn.execute("ALTER TABLE web ADD COLUMN last_entry_id TEXT")
                    logger.info("Added last_entry_id column to web")

                # feed_history migration
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS feed_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        entry_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(url) REFERENCES web(url) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_history_url ON feed_history(url)")
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_feed_history_url_entry ON feed_history(url, entry_id)")

                # bot_settings migration
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS bot_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """
                )
        except Exception as e:
            logger.warning("Database schema migration: %s", e)

    def _enable_foreign_keys(self) -> None:
        """Enables SQLite foreign key constraints"""
        with self._get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")

    def _execute_schema_script(self) -> None:
        """Executes database initialization SQL schema script"""
        schema_file = Path(__file__).resolve().parent.parent / "database" / "setup.sql"

        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema = f.read()

            with self._get_connection() as conn:
                conn.executescript(schema)
            logger.info("Database schema initialized successfully")

        except Exception as e:
            logger.error("Error initializing database: %s", str(e))
            raise RuntimeError("Unable to initialize database") from e

    @contextmanager
    def _get_connection(self):
        """Yields a database connection with auto-commit and closure"""
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def get_all_feeds(self) -> List[Tuple[str, Any, str, Optional[str]]]:
        """Returns all feeds with active subscribers"""
        query = """
            SELECT DISTINCT w.url, w.last_updated, w.last_title, w.last_entry_id
            FROM web w
            JOIN web_user wu ON w.url = wu.url
            JOIN user u ON wu.telegram_id = u.telegram_id
            WHERE u.is_active = 1
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.fetchall()

    def get_active_users_for_feed(self, url: str) -> List[Tuple[int, bool, str, str]]:
        """Returns active user IDs, Telegraph preference, alias and filter rules for a feed"""
        query = """
            SELECT wu.telegram_id, wu.telegraph, wu.alias, COALESCE(wu.filter_rules, '')
            FROM web_user wu
            JOIN user u ON wu.telegram_id = u.telegram_id
            WHERE wu.url = ? AND u.is_active = 1
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, (url,))
            return [(row[0], bool(row[1]), str(row[2]), str(row[3])) for row in cursor.fetchall()]

    def update_feed(self, url: str, last_updated: Any, last_title: str, last_entry_id: Optional[str]) -> None:
        """Updates metadata for a feed, including latest entry ID."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE web SET last_updated = ?, last_title = ?, last_entry_id = ? WHERE url = ?",
                (str(last_updated), last_title, last_entry_id, url),
            )

    def get_recent_entry_ids(self, url: str, limit: int = 50) -> List[str]:
        """Returns the most recently recorded entry IDs for a feed up to limit (default 50)."""
        query = """
            SELECT entry_id
            FROM feed_history
            WHERE url = ?
            ORDER BY id DESC
            LIMIT ?
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, (url, limit))
            return [row[0] for row in cursor.fetchall()]

    def record_feed_entries(self, url: str, entry_ids: List[str], max_keep: int = 50) -> None:
        """Records newly seen entry IDs for a feed and prunes older records beyond max_keep (default 50)."""
        if not entry_ids:
            return

        with self._get_connection() as conn:
            for eid in entry_ids:
                conn.execute(
                    """
                    INSERT INTO feed_history (url, entry_id)
                    VALUES (?, ?)
                    ON CONFLICT(url, entry_id) DO UPDATE SET created_at = CURRENT_TIMESTAMP
                    """,
                    (url, str(eid)),
                )

            # Keep at least max_keep recent items per feed
            conn.execute(
                """
                DELETE FROM feed_history
                WHERE url = ? AND id NOT IN (
                    SELECT id FROM feed_history
                    WHERE url = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (url, url, max_keep),
            )

    # User management methods
    def add_user(
        self,
        telegram_id: int,
        username: Optional[str],
        firstname: str,
        lastname: Optional[str],
        language_code: Optional[str],
        is_bot: bool,
        is_active: bool = True,
    ) -> None:
        """Adds or updates a user in the database"""
        query = """
            INSERT INTO user (telegram_id, username, firstname, lastname, 
                            language, is_bot, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                firstname = excluded.firstname,
                lastname = excluded.lastname,
                language = excluded.language,
                is_bot = excluded.is_bot,
                is_active = excluded.is_active
        """
        params = (
            telegram_id,
            username,
            firstname,
            lastname,
            language_code,
            int(is_bot),
            int(is_active),
        )

        with self._get_connection() as conn:
            conn.execute(query, params)

    def remove_user(self, telegram_id: int) -> None:
        """Removes a user and all associated bookmarks"""
        query = "DELETE FROM user WHERE telegram_id = ?"
        with self._get_connection() as conn:
            conn.execute(query, (telegram_id,))

    def update_user(self, telegram_id: int, **kwargs) -> None:
        """Updates user data"""
        if not kwargs:
            return

        set_clause = ", ".join([f"{key} = ?" for key in kwargs])
        query = f"""
            UPDATE user 
            SET {set_clause}
            WHERE telegram_id = ?
        """
        params = list(kwargs.values()) + [telegram_id]

        with self._get_connection() as conn:
            conn.execute(query, params)

    def get_user(self, telegram_id: int) -> Optional[Tuple]:
        """Retrieves a user by ID"""
        query = "SELECT * FROM user WHERE telegram_id = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(query, (telegram_id,))
            return cursor.fetchone()

    def deactivate_user(self, telegram_id: int) -> None:
        """Deactivates a user"""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE user SET is_active = 0 WHERE telegram_id = ?", (telegram_id,)
            )

    # Feed management methods
    def add_url(self, url: str) -> None:
        """Adds a feed URL to the database"""
        if not self._is_valid_url(url):
            raise ValueError("Invalid URL")

        query = """
            INSERT INTO web (url, last_title, last_updated, last_entry_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO NOTHING
        """
        params = (url, "", str(dh.parse_datetime("01-05-1999")), None)

        with self._get_connection() as conn:
            conn.execute(query, params)

    def remove_url(self, url: str) -> None:
        """Removes a feed and cascades to user bookmarks"""
        query = "DELETE FROM web WHERE url = ?"
        with self._get_connection() as conn:
            conn.execute(query, (url,))

    def update_url(self, url: str, **kwargs) -> None:
        """Updates feed data"""
        if not kwargs:
            return

        set_clause = ", ".join([f"{key} = ?" for key in kwargs])
        query = f"""
            UPDATE web 
            SET {set_clause}
            WHERE url = ?
        """
        params = list(kwargs.values()) + [url]

        with self._get_connection() as conn:
            conn.execute(query, params)

    def get_url(self, url: str) -> Optional[Tuple]:
        """Retrieves a feed by URL"""
        query = "SELECT * FROM web WHERE url = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(query, (url,))
            return cursor.fetchone()

    def get_all_urls(self) -> List[Tuple]:
        """Returns all registered feeds"""
        query = "SELECT * FROM web"
        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.fetchall()

    # User bookmark methods
    def add_user_bookmark(
        self, telegram_id: int, url: str, alias: str, telegraph: bool = False
    ) -> None:
        """Adds a bookmark for a user, ensuring the user exists in database"""
        # Ensure user exists to prevent foreign key violations
        if not self.get_user(telegram_id):
            self.add_user(
                telegram_id=telegram_id,
                username=None,
                firstname="User",
                lastname=None,
                language_code=None,
                is_bot=False,
                is_active=True,
            )

        try:
            self.add_url(url)
        except ValueError:
            logger.warning("Feed already exists: %s", url)

        query = """
            INSERT INTO web_user (url, telegram_id, alias, telegraph)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url, telegram_id) DO UPDATE SET
                alias = excluded.alias,
                telegraph = excluded.telegraph
        """
        params = (url, telegram_id, str(alias).strip(), int(telegraph))

        with self._get_connection() as conn:
            conn.execute(query, params)

    def remove_user_bookmark(self, telegram_id: int, url: str) -> None:
        """Removes a bookmark for a user"""
        query = """
            DELETE FROM web_user 
            WHERE telegram_id = ? AND url = ?
        """
        with self._get_connection() as conn:
            conn.execute(query, (telegram_id, url))

    def update_user_bookmark(
        self,
        telegram_id: int,
        url: str,
        alias: Optional[str] = None,
        telegraph: Optional[bool] = None,
    ) -> None:
        """Updates an existing bookmark"""
        updates = {}
        if alias is not None:
            updates["alias"] = alias.strip()
        if telegraph is not None:
            updates["telegraph"] = int(telegraph)

        if not updates:
            return

        set_clause = ", ".join([f"{key} = ?" for key in updates])
        query = f"""
            UPDATE web_user 
            SET {set_clause}
            WHERE telegram_id = ? AND url = ?
        """
        params = list(updates.values()) + [telegram_id, url]

        with self._get_connection() as conn:
            conn.execute(query, params)

    def get_user_bookmark(self, telegram_id: int, alias: str) -> Optional[Tuple]:
        """Retrieves a bookmark by user alias"""
        query = """
            SELECT w.url, wu.alias, w.last_updated, wu.telegraph
            FROM web_user wu
            JOIN web w ON wu.url = w.url
            WHERE wu.telegram_id = ? AND wu.alias = ?
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, (telegram_id, str(alias).strip() if alias else ""))
            return cursor.fetchone()

    def get_urls_for_user(self, telegram_id: int) -> List[Tuple]:
        """Returns all bookmarks for a user including filters and link mode"""
        query = """
            SELECT w.url, wu.alias, w.last_updated, w.last_title, COALESCE(wu.filter_rules, ''), COALESCE(wu.telegraph, 0)
            FROM web_user wu
            JOIN web w ON wu.url = w.url
            WHERE wu.telegram_id = ?
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, (telegram_id,))
            return cursor.fetchall()

    def update_user_bookmark_filter(self, telegram_id: int, alias: str, filter_rules: str) -> bool:
        """Updates filter rules for a user bookmark"""
        query = "UPDATE web_user SET filter_rules = ? WHERE telegram_id = ? AND alias = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(query, (str(filter_rules).strip(), telegram_id, str(alias).strip()))
            return cursor.rowcount > 0

    def get_users_for_url(self, url: str) -> List[Tuple]:
        """Returns all users subscribed to a feed"""
        query = """
            SELECT u.*, wu.alias, wu.telegraph
            FROM web_user wu
            JOIN user u ON wu.telegram_id = u.telegram_id
            WHERE wu.url = ?
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, (url,))
            return cursor.fetchall()

    def get_total_users(self, active_only: bool = False) -> int:
        """Counts total users"""
        query = "SELECT COUNT(*) FROM user"
        if active_only:
            query += " WHERE is_active = 1"

        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.fetchone()[0]

    def get_all_active_user_ids(self) -> List[int]:
        """Returns list of telegram IDs for all active users"""
        query = "SELECT telegram_id FROM user WHERE is_active = 1 ORDER BY telegram_id ASC"
        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return [row[0] for row in cursor.fetchall()]

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a persistent setting value from bot_settings"""
        query = "SELECT value FROM bot_settings WHERE key = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (str(key),))
                row = cursor.fetchone()
                return str(row[0]) if row else default
        except Exception as e:
            logger.warning(f"Error fetching setting {key}: {e}")
            return default

    def set_setting(self, key: str, value: Any) -> None:
        """Saves or updates a persistent setting in bot_settings"""
        query = """
            INSERT INTO bot_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """
        with self._get_connection() as conn:
            conn.execute(query, (str(key), str(value)))

    def get_system_stats(self) -> dict:
        """Aggregates system and database statistics for admin dashboard"""
        with self._get_connection() as conn:
            total_users = conn.execute("SELECT COUNT(*) FROM user").fetchone()[0]
            active_users = conn.execute("SELECT COUNT(*) FROM user WHERE is_active = 1").fetchone()[0]
            total_feeds = conn.execute("SELECT COUNT(*) FROM web").fetchone()[0]
            active_feeds = conn.execute(
                """
                SELECT COUNT(DISTINCT w.url)
                FROM web w
                JOIN web_user wu ON w.url = wu.url
                JOIN user u ON wu.telegram_id = u.telegram_id
                WHERE u.is_active = 1
                """
            ).fetchone()[0]
            total_subscriptions = conn.execute("SELECT COUNT(*) FROM web_user").fetchone()[0]
            total_history = conn.execute("SELECT COUNT(*) FROM feed_history").fetchone()[0]

        db_size_bytes = 0
        if os.path.exists(self.database_path):
            db_size_bytes = os.path.getsize(self.database_path)

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_feeds": total_feeds,
            "active_feeds": active_feeds,
            "total_subscriptions": total_subscriptions,
            "total_history": total_history,
            "db_size_bytes": db_size_bytes,
        }

    def prune_orphaned_feeds(self) -> int:
        """
        Removes feeds that have 0 active or inactive subscribers, cleaning up orphaned database rows.
        Returns the number of pruned feeds.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM web
                WHERE url NOT IN (SELECT DISTINCT url FROM web_user)
                """
            )
            pruned_count = cursor.rowcount
        logger.info(f"Pruned {pruned_count} orphaned feeds from database")
        return pruned_count

    # Validation methods
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Validates a URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def _validate_alias(alias: str) -> None:
        """Validates alias format"""
        if not 1 <= len(alias) <= 64:
            raise ValueError("Alias must be between 1 and 64 characters")


