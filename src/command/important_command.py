import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# -----
from utils.make_text import bip_bop


def get_list_handler(feed_list, telegram_user):
    """
    Create the message and the keyboard when user calls /get
    """
    keyboard = []
    user_name = html.escape(getattr(telegram_user, "first_name", None) or getattr(telegram_user, "name", "Human"))
    message = (
        f"Ok🫡 {user_name}, if you want to <b>GET</b> some Feed <b>NOW</b> tap on the button below⬇️"
    )

    if not feed_list:
        message = (
            "Well, it looks like you don't have any feeds saved🫢"
            f"{bip_bop()}.\nIf you don't know what to do, type <b>/help</b>!!"
        )
        keyboard_markup = InlineKeyboardMarkup([])
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
        keyboard_markup = InlineKeyboardMarkup(keyboard)

    return message, keyboard_markup


def remove_list_handler(feed_list, telegram_user):
    """
    Create the message and the keyboard when user calls /remove
    """
    keyboard = []
    user_name = html.escape(getattr(telegram_user, "first_name", None) or getattr(telegram_user, "name", "Human"))
    message = (
        f"Ok🫡 {user_name}, if you want to <b>REMOVE</b> a feed tap on the button below⬇️"
    )

    if not feed_list:
        message = (
            "Well, it looks like you don't have any feeds saved🫢"
            f"{bip_bop()}.\nIf you don't know what to do, type <b>/help</b>!!"
        )
        keyboard_markup = InlineKeyboardMarkup([])
    else:
        for entities in feed_list:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"❌ {entities[1]} ❌",
                        callback_data={
                            "option": "delete_feed",
                            "alias": entities[1],
                            "url": entities[0],
                            "user": telegram_user.id,
                        },
                    )
                ]
            )
        keyboard_markup = InlineKeyboardMarkup(keyboard)

    return message, keyboard_markup




