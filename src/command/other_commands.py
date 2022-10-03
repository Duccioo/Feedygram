from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# -----
from utils.make_text import number_to_emoji, random_emoji


def list_handler(db_telegraph, alias, url, index):
    if db_telegraph == True:
        new_link = "✳️Normal Link✳️k"
        old_link = "🤙Telegraph Link🤙"
    else:
        new_link = "🤙Telegraph Link🤙"
        old_link = "✳️Normal Link✳️"

    message = (
        number_to_emoji(str(index + 1))
        + " '"
        + alias
        + "' ("
        + url
        + ")"
        + "\nDefault link: <b>"
        + old_link
        + "</b>"
    )
    keyboard = [
        [
            InlineKeyboardButton(
                "🔗Change to " + new_link,
                callback_data={
                    "option": "change_database",
                    "alias": alias,
                    "url": url,
                    "set_telegraph": not db_telegraph,
                },
            )
        ],
    ]
    return message, InlineKeyboardMarkup(keyboard)


def help_message():
    return (
        "Need help? No Problem!!\n<b>QUICK START:</b>\n\n"
        + " *️⃣For add new RSS url type: <code>/add *your_RSS_url*</code>\n<i>(optional)</i> if you want to give a name for that entry try: <code>/add *your_RSS_url* *name_of_entry*\n\n"
        + "*️⃣For remove a feed type <code>/remove</code> and then click the target feed\n\n"
        + "*️⃣For change the default link type try <code>/list</code> then click the button below of your target link\n\n"
        +"*️⃣For get an instant article try to type <code>/get</code> then select your feed and then select how many articles do you want to receive!\n\n"
        +"*️⃣If you want to know more about this bot try <code>/about</code>"
    )


def stop_handler(db, telegram_user):
    db.update_user(telegram_id=telegram_user.id, is_active=0)
    return "Oh.. Okay, I will not send you any more news updates! If you change your mind and you want to receive messages from me again use /start command again!"


def about_message(number):
    message = (
        "Hi🙃! Hope you are finding this bot useful, if so then spread the word and tell your friends about <a href='https://t.me/feedygram_bot'>🐕Feedygram</a>!!\n"
        + "There are currently "
        + str(number_to_emoji((number[0][0])))
        + " active users\n"
        "\nThis bot was made with passion "
        + random_emoji()
        + " by Duccio Meconcelli on the base of <a href='https://github.com/hamitdurmus/robotrss'> RobotRSS by hamitdurmus </a>\n\n"
        + "The telegraph <a href='https://github.com/NullPointerMaker/webpage2telegraph'>webpage converter library</a> was made by <a href='https://github.com/NullPointerMaker'>NullPointerMaker</a> \n\n"
        + "For more info check the github page: <a href='https://github.com/Duccioo/Feedygram'>Feedygram</a>\n"
        + "And for other stuff I made check my website: <a href='https://duccio.me/'>duccio.me</a>\n"
        +"<i>🐶Bau Bau🐶</i>"
    )
    return message
