import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# -----
from utils.make_text import number_to_emoji, random_emoji


def list_handler(db_telegraph, alias, url, index):
    if db_telegraph:
        new_link = "✳️Normal Link✳️"
        old_link = "🤙Telegraph Link🤙"
    else:
        new_link = "🤙Telegraph Link🤙"
        old_link = "✳️Normal Link✳️"

    safe_alias = html.escape(str(alias))
    safe_url = html.escape(str(url))

    message = (
        f"{number_to_emoji(str(index + 1))}: '<b>{safe_alias}</b>'\n"
        f"Link: <code>{safe_url}</code>\n"
        f"Default link type: <b>{old_link}</b>"
    )
    keyboard = [
        [
            InlineKeyboardButton(
                "🔗Change to " + new_link,
                callback_data={
                    "option": "change_database",
                    "alias": alias,
                    "url": url,
                    "set_telegraph": not bool(db_telegraph),
                },
            )
        ],
    ]
    return message, InlineKeyboardMarkup(keyboard)


def help_message():
    return (
        "Need help? No Problem!!\n<b>QUICK START:</b>\n\n"
        "💡 <i>Tip: Use the buttons on your keyboard below for one-tap navigation!</i>\n\n"
        "📖 <b>My Feeds:</b> Tap <code>📖 My Feeds</code> or use <code>/list</code>\n"
        "🔍 <b>Explore Catalog:</b> Tap <code>🔍 Explore Feeds</code> or use <code>/explore</code>\n"
        "➕ <b>Add Feed / Website:</b> Send any URL in chat (or use <code>/add https://example.com</code>)\n"
        "• YouTube: <code>/youtube @channel</code>\n"
        "• Twitter / X: <code>/x @username</code>\n"
        "• Reddit: <code>/reddit r/technology</code>\n\n"
        "⚙️ <b>Keyword Filters:</b> Tap <code>⚙️ Keyword Filters</code> or use <code>/filter</code>\n"
        "📥 <b>Fetch Articles:</b> Tap <code>📥 Get Feeds</code> or use <code>/get</code>\n"
        "🗑️ <b>Remove Feed:</b> Tap <code>🗑️ Remove Feed</code> or use <code>/remove</code>\n"
        "💾 <b>Backup / Restore:</b> <code>/export</code> & <code>/import</code> (or send an OPML file)\n"
        "📢 <b>Channels & Groups:</b> <code>/channel</code>"
    )


def stop_handler(telegram_user, db):
    db.update_user(telegram_id=telegram_user.id, is_active=0)
    return "Oh.. Okay, I will not send you any more news updates! If you change your mind and you want to receive messages from me again use the <code>/start</code> command!"


def about_message(number: int):
    message = (
        "Hi🙃! Hope you are finding this bot useful,\n"
        "if so then spread the word and tell your friends about <a href='https://t.me/feedygram_bot'>🐕Feedygram</a>!!\n\n"
        "For more info check the <a href='https://github.com/Duccioo/Feedygram'>GitHub page</a>.\n\n"
        f"This bot was made with passion by {random_emoji()} Duccio Meconcelli (@duccioo).\n"
        "Based on <a href='https://github.com/hamitdurmus/robotrss'>RobotRSS by hamitdurmus</a>.\n\n"
        "For feedback: meconcelliduccio@gmail.com | <a href='https://duccio.me/'>duccio.me</a>\n"
        "<i>🐶Woof Woof🐶</i>\n\n"
        f"There are currently {number_to_emoji(number)} active users\n"
    )
    return message


