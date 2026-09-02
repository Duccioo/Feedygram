import html
import os
import logging
from typing import Optional, List, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.database import DatabaseHandler

logger = logging.getLogger(__name__)

DEFAULT_MAX_FEEDS = 15


def is_admin(user_id: int | str) -> bool:
    """
    Checks if given user_id has admin privileges configured in environment.
    Supports single or comma-separated user IDs in ADMIN_USER_ID or ADMIN_ID.
    """
    if not user_id:
        return False

    admin_env = os.environ.get("ADMIN_USER_ID") or os.environ.get("ADMIN_ID", "")
    if not admin_env.strip():
        return False

    admin_ids = {item.strip() for item in admin_env.split(",") if item.strip()}
    return str(user_id).strip() in admin_ids


def get_max_feeds_limit(db: DatabaseHandler) -> int:
    """
    Retrieves the maximum allowed feeds per non-admin user.
    0 means unlimited.
    Checks database settings first, then falls back to MAX_FEEDS_PER_USER env var.
    """
    db_val = db.get_setting("max_feeds_per_user")
    if db_val is not None:
        try:
            return max(0, int(db_val))
        except (ValueError, TypeError):
            pass

    env_val = os.environ.get("MAX_FEEDS_PER_USER", str(DEFAULT_MAX_FEEDS))
    try:
        return max(0, int(env_val))
    except (ValueError, TypeError):
        return DEFAULT_MAX_FEEDS


def set_max_feeds_limit(db: DatabaseHandler, limit: int) -> int:
    """
    Updates the max feeds limit in database settings.
    """
    clean_limit = max(0, int(limit))
    db.set_setting("max_feeds_per_user", str(clean_limit))
    return clean_limit


# --- Keyboard Builders ---

def make_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Creates the main inline keyboard for the Admin Dashboard"""
    keyboard = [
        [
            InlineKeyboardButton("🔢 Limite Feed Utente", callback_data={"option": "admin_action", "action": "max_feeds_menu"}),
            InlineKeyboardButton("📢 Messaggio Broadcast", callback_data={"option": "admin_action", "action": "prompt_broadcast"}),
        ],
        [
            InlineKeyboardButton("📊 Statistiche & Diagnostica", callback_data={"option": "admin_action", "action": "system_stats"}),
            InlineKeyboardButton("🔄 Sincronizzazione Forzata", callback_data={"option": "admin_action", "action": "force_sync"}),
        ],
        [
            InlineKeyboardButton("🧹 Pulizia Feed Orfani", callback_data={"option": "admin_action", "action": "clean_orphaned"}),
            InlineKeyboardButton("❌ Chiudi", callback_data={"option": "admin_action", "action": "close"}),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def make_max_feeds_keyboard(current_limit: int) -> InlineKeyboardMarkup:
    """Creates inline keyboard to view and adjust the max feeds limit"""
    limit_text = "♾️ Illimitati" if current_limit == 0 else str(current_limit)
    keyboard = [
        [
            InlineKeyboardButton("➖ 5", callback_data={"option": "admin_action", "action": "adjust_limit", "delta": -5}),
            InlineKeyboardButton("➖ 1", callback_data={"option": "admin_action", "action": "adjust_limit", "delta": -1}),
            InlineKeyboardButton(f"[ {limit_text} ]", callback_data={"option": "admin_action", "action": "noop"}),
            InlineKeyboardButton("➕ 1", callback_data={"option": "admin_action", "action": "adjust_limit", "delta": 1}),
            InlineKeyboardButton("➕ 5", callback_data={"option": "admin_action", "action": "adjust_limit", "delta": 5}),
        ],
        [
            InlineKeyboardButton("10", callback_data={"option": "admin_action", "action": "set_limit", "value": 10}),
            InlineKeyboardButton("15", callback_data={"option": "admin_action", "action": "set_limit", "value": 15}),
            InlineKeyboardButton("25", callback_data={"option": "admin_action", "action": "set_limit", "value": 25}),
            InlineKeyboardButton("50", callback_data={"option": "admin_action", "action": "set_limit", "value": 50}),
            InlineKeyboardButton("♾️ Illimitati", callback_data={"option": "admin_action", "action": "set_limit", "value": 0}),
        ],
        [
            InlineKeyboardButton("🔙 Torna alla Dashboard", callback_data={"option": "admin_action", "action": "show_menu"}),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def make_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Creates confirmation inline keyboard before dispatching broadcast message"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Conferma e Invia a Tutti", callback_data={"option": "admin_action", "action": "confirm_broadcast"}),
        ],
        [
            InlineKeyboardButton("❌ Annulla", callback_data={"option": "admin_action", "action": "cancel_broadcast"}),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def make_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Creates simple back button to admin dashboard"""
    keyboard = [
        [
            InlineKeyboardButton("🔙 Torna alla Dashboard", callback_data={"option": "admin_action", "action": "show_menu"}),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Message Formatters ---

def format_admin_dashboard_message(stats: dict, current_limit: int, admin_user: Any = None) -> str:
    """Generates clean HTML text for the admin dashboard home screen"""
    name = "Admin"
    if admin_user:
        name = getattr(admin_user, "first_name", None) or getattr(admin_user, "username", "Admin")
    safe_name = html.escape(str(name))

    limit_str = "♾️ Illimitati" if current_limit == 0 else f"<b>{current_limit}</b> feed/utente"

    return (
        f"👑 <b>Dashboard Amministratore Feedygram</b>\n\n"
        f"Benvenuto, <b>{safe_name}</b>!\n\n"
        f"📊 <b>Panoramica Veloce:</b>\n"
        f"• 👥 Utenti Attivi: <b>{stats.get('active_users', 0)}</b> / {stats.get('total_users', 0)}\n"
        f"• 📡 Feed Monitorati: <b>{stats.get('active_feeds', 0)}</b>\n"
        f"• 🔢 Limite Feed: {limit_str} <i>(Tu: Illimitati)</i>\n\n"
        f"Scegli una delle opzioni qui sotto per gestire il bot:"
    )


def format_system_stats_message(stats: dict, provider_name: str, interval: int) -> str:
    """Generates detailed diagnostic message for admin"""
    db_size = stats.get("db_size_bytes", 0)
    if db_size > 1024 * 1024:
        db_size_str = f"{db_size / (1024 * 1024):.2f} MB"
    elif db_size > 1024:
        db_size_str = f"{db_size / 1024:.1f} KB"
    else:
        db_size_str = f"{db_size} B"

    return (
        f"📊 <b>Statistiche & Diagnostica di Sistema</b>\n\n"
        f"👥 <b>Utenti:</b>\n"
        f"• Attivi: <b>{stats.get('active_users', 0)}</b>\n"
        f"• Registrati Totali: <b>{stats.get('total_users', 0)}</b>\n\n"
        f"📡 <b>Feed & Abbonamenti:</b>\n"
        f"• Feed Monitorati Attivamente: <b>{stats.get('active_feeds', 0)}</b>\n"
        f"• Feed nel Database: <b>{stats.get('total_feeds', 0)}</b>\n"
        f"• Totale Abbonamenti Utenti: <b>{stats.get('total_subscriptions', 0)}</b>\n"
        f"• Articoli Archiviati (Deduplicazione): <b>{stats.get('total_history', 0)}</b>\n\n"
        f"⚙️ <b>Motore & Configurazione:</b>\n"
        f"• Provider RSS: <code>{html.escape(provider_name)}</code>\n"
        f"• Intervallo Polling: <b>{interval}s</b> (~{interval // 60} min)\n"
        f"• Dimensione Database SQLite: <b>{db_size_str}</b>\n"
    )
