import html
from typing import Dict, List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

PRESETS_DATA: Dict[str, List[Dict[str, str]]] = {
    "💻 Tech & Dev": [
        {"name": "Hacker News", "url": "https://news.ycombinator.com/rss"},
        {"name": "GitHub Trending Weekly", "url": "https://duccioo.github.io/GitHubTrendingRSS/feeds/all_languages_weekly.xml"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    ],
    "🌍 News & World": [
        {"name": "BBC Top Stories", "url": "http://feeds.bbci.co.uk/news/rss.xml"},
        {"name": "ANSA Notizie", "url": "https://www.ansa.it/sito/ansait_rss.xml"},
        {"name": "Il Post", "url": "https://www.ilpost.it/feed/"},
    ],
    "🎮 Gaming & Entertainment": [
        {"name": "Eurogamer", "url": "https://www.eurogamer.net/feed"},
        {"name": "IGN News", "url": "https://feeds.feedburner.com/ign/news"},
    ],
    "🔬 Science & Space": [
        {"name": "NASA Breaking News", "url": "https://www.nasa.gov/feed/"},
        {"name": "Nature News", "url": "https://www.nature.com/nature.rss"},
    ],
}


def make_categories_keyboard() -> InlineKeyboardMarkup:
    """Genera la tastiera per selezionare una categoria di preset."""
    keyboard = []
    for cat in PRESETS_DATA.keys():
        keyboard.append([
            InlineKeyboardButton(
                cat,
                callback_data={"option": "explore_category", "cat": cat}
            )
        ])
    return InlineKeyboardMarkup(keyboard)


def make_category_feeds_keyboard(category: str) -> Tuple[str, InlineKeyboardMarkup]:
    """Genera il messaggio e i bottoni di iscrizione per una specifica categoria."""
    feeds = PRESETS_DATA.get(category, [])
    if not feeds:
        return "Nessun feed trovato in questa categoria.", make_categories_keyboard()

    safe_cat = html.escape(category)
    message = (
        f"<b>{safe_cat}</b>\n\n"
        "Tocca un feed per aggiungerlo istantaneamente alle tue sottoscrizioni:"
    )

    keyboard = []
    for f in feeds:
        keyboard.append([
            InlineKeyboardButton(
                f"➕ {f['name']}",
                callback_data={
                    "option": "add_preset",
                    "name": f["name"],
                    "url": f["url"],
                    "cat": category,
                }
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            "🔙 Torna alle Categorie",
            callback_data={"option": "explore_categories"}
        )
    ])

    return message, InlineKeyboardMarkup(keyboard)
