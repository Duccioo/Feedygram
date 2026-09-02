import html
import random
import re
from typing import Optional

EMOJIS = [
    "📰", "⚡", "✨", "🍕", "🔥", "🚀", "💡", "📡", "🐕", "☕",
    "🌍", "📚", "🎮", "🛠️", "🎯", "🌟", "📣", "🤖", "📌", "💬",
]


def random_emoji() -> str:
    """Returns a safe, universally renderable random emoji."""
    return random.choice(EMOJIS)


def number_to_emoji(number: int | str) -> str:
    """Converts a number into a sequence of numeric emojis."""
    legend = {
        "0": "0️⃣",
        "1": "1️⃣",
        "2": "2️⃣",
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣",
        "7": "7️⃣",
        "8": "8️⃣",
        "9": "9️⃣",
    }
    return "".join(legend.get(c, c) + " " for c in str(number)).strip()


def bip_bop() -> str:
    """Returns a random robotic bleep string for bot messages."""
    return random.choice([
        " BIP BOP ",
        " BOP PIP ",
        " BUP BIP ",
        " BI BI BIP ",
        " PIP BUP ",
    ])


def clean_feed_text(raw: Optional[str]) -> str:
    """
    Cleans raw feed text:
    1. Unescapes HTML entities (e.g. &#8216; -> ‘, &#8217; -> ’, &amp; -> &, &quot; -> ").
    2. Supports multi-pass unescaping for double-encoded entities (e.g. &amp;#8216;).
    3. Strips embedded HTML formatting tags (<p>, <b>, <i>, <span>, etc.) while preserving mathematical brackets.
    4. Normalizes special whitespace (non-breaking spaces, zero-width spaces).
    """
    if not raw:
        return ""

    text = str(raw)

    # Strip CDATA tags if present
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)

    # Iterative HTML entity unescaping (up to 3 passes to handle multiply-escaped strings)
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded

    # Strip common HTML presentation/layout tags with word boundary to avoid stripping math or generics
    text = re.sub(
        r"<\/?(?:b|i|u|s|em|strong|span|p|a|br|div|small|h[1-6]|font|article|section|figure|figcaption)\b[^>]*>",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Normalize special/invisible spaces
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")

    # Collapse multiple whitespaces and strip margins
    return " ".join(text.split())


