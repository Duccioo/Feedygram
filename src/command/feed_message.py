from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import webpage2telegraph
import random
from utils.datehandler import DateHandler


async def send_newest_messages(self, url, post, user):

    set_telegraph = user[8]
    post_update_date = DateHandler.parse_datetime(datetime=post.updated)
    url_update_date = DateHandler.parse_datetime(datetime=url[1])

    if post_update_date > url_update_date:
        if set_telegraph:
            reply_markup = make_feed_keyboard(
                "✳️Normal Link✳️", user[7], False, post.link, post.title
            )

            title_first = post.title
            link_first = str(webpage2telegraph.transfer(post.link))
            title_second = "Normal Link"
            link_second = post.link
        else:
            reply_markup = make_feed_keyboard(
                "🤙Telegraph Link🤙", user[7], True, post.link, post.title
            )

            title_first = post.title
            link_first = post.link
            title_second = "Telegraph Link"
            link_second = str(webpage2telegraph.transfer(post.link))

        list = [
            "New Update! ",
            "Something Change in ",
            "Here's for you, from",
            "Drin drin! ",
            "News FROM ",
        ]

        message = (
            "🔔"
            + random.choice(list)
            + "["
            + user[7]
            + "] \n--------------------------------------------------\n <a href='"
            + link_first
            + "'>"
            + title_first
            + "</a>"
            + "\n--------------------------------------------------\n<a href='"
            + link_second
            + "'>"
            + "["
            + title_second
            + "]"
            + "</a>"
        )

        try:
            await self.bot.bot.send_message(
                chat_id=user[0],
                text=message,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

        except TelegramError:
            print(TelegramError)
            # handle all other telegram related errors
            pass


def make_feed_keyboard(name="", alias="", set_telegraph=False, link="", title=""):
    keyboard = [
        [
            InlineKeyboardButton(
                name,
                callback_data={
                    "alias": alias,
                    "set_telegraph": set_telegraph,
                    "link": link,
                    "title": title,
                },
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def send_check_message(
    update,
    message="",
    reply_markup=None,
):
    if update.callback_query != None:
        await update.callback_query.edit_message_text(
            text=message,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    else:
        await update.bot.send_message(
            chat_id=update.message.from_user.id,
            text=message,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


async def update_message(
    update,
    context,
    url,
    post,
    user,
):

    query = update.callback_query
    if query != None:
        await query.answer()
        data = query.data
    else:
        data = {"alias": "", "link": "", "title": ""}

    set_telegraph = data["set_telegraph"]

    if set_telegraph:
        reply_markup = make_feed_keyboard(
            "✳️Normal Link✳️", data["alias"], False, data["link"], data["title"]
        )

        title_first = data["title"]
        link_first = str(webpage2telegraph.transfer(data["link"]))
        title_second = "Normal Link"
        link_second = data["link"]
    else:
        reply_markup = make_feed_keyboard(
            "🤙Telegraph Link🤙", data["alias"], True, data["link"], data["title"]
        )

        title_first = data["title"]
        link_first = data["link"]
        title_second = "Telegraph Link"
        link_second = str(webpage2telegraph.transfer(data["link"]))

    list = [
        "New Update! ",
        "Something Change in ",
        "Here's for you, from",
        "Drin drin! ",
        "News FROM ",
    ]
    message = (
        "🔔"
        + random.choice(list)
        + "["
        + data["alias"]
        + "] \n--------------------------------------------------\n <a href='"
        + link_first
        + "'>"
        + title_first
        + "</a>"
        + "\n--------------------------------------------------\n<a href='"
        + link_second
        + "'>"
        + "["
        + title_second
        + "]"
        + "</a>"
    )

    try:

        await send_check_message(update, message=message, reply_markup=reply_markup)

    except:
        print("dio porco")
        # handle all other telegram related errors
        pass
