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

# Configurazione logging
logger = logging.getLogger(__name__)


class DatabaseHandler:
    def __init__(self, *database_path: str):
        base_dir = Path(__file__).resolve().parent.parent
        self.database_path = str(base_dir.joinpath(*database_path))
        logger.info("Database path: %s", self.database_path)

        self._init_database()
        self._enable_foreign_keys()

    def _init_database(self) -> None:
        """Inizializza il database se non esiste ed esegue migrazioni necessarie"""
        db_dir = os.path.dirname(self.database_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        if not os.path.exists(self.database_path):
            logger.info("Creazione nuovo database: %s", self.database_path)
            self._execute_schema_script()
        else:
            self._run_migrations()

    def _run_migrations(self) -> None:
        """Applica modifiche allo schema per database già esistenti"""
        try:
            with self._get_connection() as conn:
                # Migrazione web_user (filter_rules)
                cursor = conn.execute("PRAGMA table_info(web_user)")
                columns_wu = [row[1] for row in cursor.fetchall()]
                if "filter_rules" not in columns_wu:
                    conn.execute("ALTER TABLE web_user ADD COLUMN filter_rules TEXT DEFAULT ''")
                    logger.info("Aggiunta colonna filter_rules a web_user")

                # Migrazione web (last_entry_id)
                cursor = conn.execute("PRAGMA table_info(web)")
                columns_w = [row[1] for row in cursor.fetchall()]
                if "last_entry_id" not in columns_w:
                    conn.execute("ALTER TABLE web ADD COLUMN last_entry_id TEXT")
                    logger.info("Aggiunta colonna last_entry_id a web")
        except Exception as e:
            logger.warning("Migrazione schema database: %s", e)

    def _enable_foreign_keys(self) -> None:
        """Abilita i vincoli di foreign key"""
        with self._get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")

    def _execute_schema_script(self) -> None:
        """Esegue lo script di inizializzazione del database"""
        schema_file = Path(__file__).resolve().parent.parent / "database" / "setup.sql"

        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema = f.read()

            with self._get_connection() as conn:
                conn.executescript(schema)
            logger.info("Schema database inizializzato correttamente")

        except Exception as e:
            logger.error("Errore nell'inizializzazione del database: %s", str(e))
            raise RuntimeError("Impossibile inizializzare il database") from e

    @contextmanager
    def _get_connection(self):
        """Restituisce una connessione al database garantendone commit e chiusura"""
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def get_all_feeds(self) -> List[Tuple[str, Any, str, Optional[str]]]:
        """Restituisce tutti i feed con iscritti attivi"""
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
        """Restituisce gli ID utente attivi, preferenza Telegraph, alias e regole di filtro per un feed"""
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
        """Aggiorna i metadati di un feed, incluso l'ID dell'ultimo entry."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE web SET last_updated = ?, last_title = ?, last_entry_id = ? WHERE url = ?",
                (str(last_updated), last_title, last_entry_id, url),
            )

    # Metodi per la gestione degli utenti
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
        """Aggiunge o aggiorna un utente al database"""
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
        """Rimuove un utente e tutti i suoi collegamenti"""
        query = "DELETE FROM user WHERE telegram_id = ?"
        with self._get_connection() as conn:
            conn.execute(query, (telegram_id,))

    def update_user(self, telegram_id: int, **kwargs) -> None:
        """Aggiorna i dati di un utente"""
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
        """Recupera un utente per ID"""
        query = "SELECT * FROM user WHERE telegram_id = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(query, (telegram_id,))
            return cursor.fetchone()

    def deactivate_user(self, telegram_id: int) -> None:
        """Disattiva un utente"""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE user SET is_active = 0 WHERE telegram_id = ?", (telegram_id,)
            )

    # Metodi per la gestione dei feed
    def add_url(self, url: str) -> None:
        """Aggiunge un feed al database"""
        if not self._is_valid_url(url):
            raise ValueError("URL non valido")

        query = """
            INSERT INTO web (url, last_title, last_updated, last_entry_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO NOTHING
        """
        params = (url, "", str(dh.parse_datetime("01-05-1999")), None)

        with self._get_connection() as conn:
            conn.execute(query, params)

    def remove_url(self, url: str) -> None:
        """Rimuove un feed e tutti i collegamenti utente"""
        query = "DELETE FROM web WHERE url = ?"
        with self._get_connection() as conn:
            conn.execute(query, (url,))

    def update_url(self, url: str, **kwargs) -> None:
        """Aggiorna i dati di un feed"""
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
        """Recupera un feed per URL"""
        query = "SELECT * FROM web WHERE url = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(query, (url,))
            return cursor.fetchone()

    def get_all_urls(self) -> List[Tuple]:
        """Restituisce tutti i feed registrati"""
        query = "SELECT * FROM web"
        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.fetchall()

    # Metodi per i bookmark degli utenti
    def add_user_bookmark(
        self, telegram_id: int, url: str, alias: str, telegraph: bool = False
    ) -> None:
        """Aggiunge un bookmark per un utente, assicurando che l'utente esista nel database"""
        # Assicura che l'utente esista per evitare violazioni di foreign key
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
            logger.warning("Feed già esistente: %s", url)

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
        """Rimuove un bookmark per un utente"""
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
        """Aggiorna un bookmark esistente"""
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
        """Recupera un bookmark per alias utente"""
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
        """Restituisce tutti i bookmark di un utente inclusi filtri e modalità link"""
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
        """Aggiorna le regole di filtro per un bookmark utente"""
        query = "UPDATE web_user SET filter_rules = ? WHERE telegram_id = ? AND alias = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(query, (str(filter_rules).strip(), telegram_id, str(alias).strip()))
            return cursor.rowcount > 0

    def get_users_for_url(self, url: str) -> List[Tuple]:
        """Restituisce tutti gli utenti iscritti a un feed"""
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
        """Conta gli utenti totali"""
        query = "SELECT COUNT(*) FROM user"
        if active_only:
            query += " WHERE is_active = 1"

        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.fetchone()[0]

    # Metodi di validazione
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Valida un URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def _validate_alias(alias: str) -> None:
        """Valida il formato di un alias"""
        if not 1 <= len(alias) <= 64:
            raise ValueError("L'alias deve essere tra 1 e 64 caratteri")

