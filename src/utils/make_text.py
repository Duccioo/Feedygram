import random

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

