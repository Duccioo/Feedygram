import html
import logging
import random
import re
from typing import Tuple, List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.link_converter import convert_to_instant_link
from utils.twitter import convert_to_fxtwitter_url

logger = logging.getLogger(__name__)

MESSAGES_LIST = [
    "New Update! ",
    "Something Changed in ",
    "Here's for you, from",
    "Drin drin! ",
    "News FROM ",
    "Hey! What's up? ",
]


def make_feed_keyboard(name: str = "", alias: str = "", set_telegraph: bool = False, link: str = "", title: str = "") -> InlineKeyboardMarkup:
    """Create inline keyboard to toggle link mode and request TL;DR"""
    toggle_data = {
        "option": "change_feed_link",
        "alias": alias,
        "set_telegraph": set_telegraph,
        "link": link,
        "title": title,
    }
    tldr_data = {
        "option": "get_tldr",
        "alias": alias,
        "link": link,
        "title": title,
    }
    keyboard = [
        [InlineKeyboardButton(name, callback_data=toggle_data)],
        [InlineKeyboardButton("📝 TL;DR Summary", callback_data=tldr_data)],
    ]
    return InlineKeyboardMarkup(keyboard)


def send_feed(
    telegraph: bool,
    alias: str,
    post_link: str,
    post_title: str,
    tags: Optional[List[str]] = None,
) -> Tuple[str, InlineKeyboardMarkup]:
    """Generate HTML-formatted text with hashtags and keyboard for an RSS item"""

    safe_title = html.escape(str(post_title).strip() if post_title else "No Title")
    safe_alias = html.escape(str(alias).strip() if alias else "Feed")

    if telegraph:
        link_first = convert_to_instant_link(post_link, title=post_title)
        reply_markup = make_feed_keyboard("✳️Normal Link✳️", alias, False, post_link, post_title)
    else:
        link_first = convert_to_fxtwitter_url(post_link)
        reply_markup = make_feed_keyboard("🤙Telegraph Link🤙", alias, True, post_link, post_title)

    hashtags = []
    if tags:
        for t in tags[:5]:
            clean_t = re.sub(r"[^\w]", "", str(t).strip())
            if clean_t and len(clean_t) >= 2 and f"#{clean_t}" not in hashtags:
                hashtags.append(f"#{clean_t}")

    safe_link = html.escape(str(link_first), quote=True)
    tags_line = f"\n🏷️ {' '.join(hashtags)}" if hashtags else ""
    prefix = random.choice(MESSAGES_LIST)
    message = (
        f"🔔{prefix}[ {safe_alias} ] "
        f'<a href="{safe_link}"><blockquote>{safe_title}</blockquote></a>'
        f"{tags_line}\n"
    )

    return message, reply_markup


