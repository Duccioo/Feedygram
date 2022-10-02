from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# -----
from utils.make_text import number_to_emoji, bip_bop, random_emoji


def get_list_handler(feed_list, telegram_user):
    """
    create the message and the keyboard when user call /remove
    """

    keyboard = []
    message = (
        "Ok🫡 ,"
        + telegram_user.name
        + ", if you want to <b>GET</b> some Feed <b>NOW</b> tap on the buttom below⬇️"
    )

    if len(feed_list) == 0:
        message = (
            "Well, it looks like you don't have any feeds saved🫢"
            + bip_bop()
            + ".\nIf you don't know what to do, type <b>/help</b>!!"
        )
        keyboard_Markup = InlineKeyboardMarkup([[]])

    else:
        for entities in feed_list:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        entities[1],
                        callback_data={
                            "option": "select_how_many_feed",
                            "alias": entities[1],
                            "url": entities[0],
                            "user": telegram_user.id,
                        },
                    )
                ]
            )
        keyboard_Markup = InlineKeyboardMarkup(keyboard)

    return message, keyboard_Markup


def remove_list_handler(feed_list, telegram_user):
    """
    create the message and the keyboard when user call /remove
    """

    keyboard = []
    message = (
        "Ok🫡 ,"
        + telegram_user.name
        + ", if you want <b>REMOVE</b> some feed tap on the buttom below⬇️"
    )

    if len(feed_list) == 0:
        message = (
            "Well, it looks like you don't have any feeds saved🫢"
            + bip_bop()
            + ".\nIf you don't know what to do, type <b>/help</b>!!"
        )
        keyboard_Markup = InlineKeyboardMarkup([[]])

    else:
        for entities in feed_list:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "❌" + entities[1] + "❌",
                        callback_data={
                            "option": "delete_feed",
                            "alias": entities[1],
                            "url": entities[0],
                            "user": telegram_user.id,
                        },
                    )
                ]
            )
        keyboard_Markup = InlineKeyboardMarkup(keyboard)

    return message, keyboard_Markup



