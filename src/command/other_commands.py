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
        + ": '"
        + alias
        + "'\nLink: <code>"
        + url
        + "</code>"
        + "\nDefault link type: <b>"
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
        + "*️⃣For add new RSS url type: <code>/add *your_RSS_url*</code>\n<i>(optional)</i> if you want to give a name for that entry try: <code>/add *your_RSS_url* *name_of_entry*</code>\n\n"
        + "*️⃣For remove a feed type <code>/remove</code> and then click the target feed\n\n"
        + "*️⃣For change the default link type try <code>/list</code> then click the button below of your target link\n\n"
        + "*️⃣For get an instant article try to type <code>/get</code> then select your feed and then select how many articles do you want to receive!\n\n"
        + "*️⃣If you want to know more about this bot try <code>/about</code>"
    )


def stop_handler(db, telegram_user):
    db.update_user(telegram_id=telegram_user.id, is_active=0)
    return "Oh.. Okay, I will not send you any more news updates! If you change your mind and you want to receive messages from me again use <code>/start</code> command again!"


def about_message(number):

    # try:
    #     _number = number[0][0]
    # except:
    #     _number = number[0]

    message = (
        "Hi🙃! Hope you are finding this bot useful,\nif so then spread the word and tell your friends about <a href='https://t.me/feedygram_bot'>🐕Feedygram</a>!!\n"
        + "For more info check the  <a href='https://github.com/Duccioo/Feedygram'>github page.</a>\n"
        "\nThis bot was made with passion by "
        + random_emoji()
        + "Duccio Meconcelli (@Dosium).\n\nBased on the <a href='https://github.com/hamitdurmus/robotrss'>RobotRSS by hamitdurmus. </a>\n"
        + "The telegraph <a href='https://github.com/NullPointerMaker/webpage2telegraph'>webpage converter library</a> was made by <a href='https://github.com/NullPointerMaker'>NullPointerMaker</a> \n\n"
        + "For other stuff I made check my GitHub: <a href='https://duccio.me/'>Duccioo</a>\n"
        + "And if you have any feedback, please reach out to me at meconcelliduccio@gmail.com or visit my website <a href='https://duccio.me/'>duccio.me</a>\n"
        + "<i>🐶Bau Bau🐶</i>"
        + "\n\nThere are currently "
        + str(number_to_emoji(number))
        + "active users\n"
    )
    return message
