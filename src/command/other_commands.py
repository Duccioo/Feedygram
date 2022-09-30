from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.make_text import number_to_emoji


def list_handler(db_telegraph, alias, url, index):

    if db_telegraph:
        new_link = "Normal Link"
        old_link = "Telegraph Link"
    else:
        new_link = "Telegraph Link"
        old_link = "Normal Link"

    message = (
        number_to_emoji(str(index + 1))
        + " '"
        + alias
        + "' ("
        + url
        + ")"
        + "\n➡️Default link: <b>"
        + old_link
        + "</b>"
    )
    keyboard = [
        [
            InlineKeyboardButton(
                "🔗Change to " + new_link + "🔗",
                callback_data={
                    "option": "change_database",
                    "alias": alias,
                    "url": url,
                },
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard), message


async def help_message():
    return "If you need help with handling the commands, please have a look at my <a href='https://github.com/cbrgm/telegram-robot-rss'>Github</a> page. There I have summarized everything necessary for you!"


async def stop_handler(db, telegram_user):
    db.update_user(telegram_id=telegram_user.id, is_active=0)

    return "Oh.. Okay, I will not send you any more news updates! If you change your mind and you want to receive messages from me again use /start command again!"


async def about_message(db):
    total_user = db.get_total_user()

    message = "" + "" + "" + "" + "In this Moment there are:" + str(total_user[0][0])
    return message
