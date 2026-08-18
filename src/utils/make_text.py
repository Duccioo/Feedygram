import random

EMOJIS = [
    "📰", "⚡", "✨", "🍕", "🔥", "🚀", "💡", "📡", "🐕", "☕",
    "🌍", "📚", "🎮", "🛠️", "🎯", "🌟", "📣", "🤖", "📌", "💬",
]


def random_emoji() -> str:
    """Restituisce un'emoji casuale sicura e universalmente renderizzabile."""
    return random.choice(EMOJIS)


def number_to_emoji(number: int | str) -> str:
    """Converte un numero in una sequenza di emoji numeriche."""
    legenda = {
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
    return "".join(legenda.get(c, c) + " " for c in str(number)).strip()


def bip_bop() -> str:
    """Restituisce una stringa robotica casuale per i messaggi del bot."""
    return random.choice([
        " BIP BOP ",
        " BOP PIP ",
        " BUP BIP ",
        " BI BI BIP ",
        " PIP BUP ",
    ])
