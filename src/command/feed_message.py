from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import webpage2telegraph
import random
import json
import logging

# ---
from utils.datehandler import DateHandler


# Aggiungi queste costanti all'inizio dello script
MAX_SAME_LINK_UPDATES = 2
MESSAGES_LIST = [
    "New Update! ",
    "Something Change in ",
    "Here's for you, from",
    "Drin drin! ",
    "News FROM ",
    "Hey! What's up? ",
    "I hate this job, but I love you. ",
]


async def send_newest_messages(self, url, post, user):
    set_telegraph = user[8]
    post_update_date = DateHandler.parse_datetime(post.updated)
    url_update_date = DateHandler.parse_datetime(url[1])

    # Estrai i nuovi campi dal database
    last_link = url[2]  # Supponendo che url[2] sia l'ultimo link salvato
    same_link_count = url[3]  # Supponendo che url[3] sia il contatore

    # Controllo combinato data e link
    if post_update_date > url_update_date:
        if post.link == last_link:
            same_link_count += 1
            if same_link_count >= MAX_SAME_LINK_UPDATES:
                # Aggiorna il database senza inviare notifiche
                await self.db_update(
                    user[0], post.updated, same_link_count=same_link_count
                )
                return
        else:
            same_link_count = 0  # Reset contatore se il link cambia

        # Aggiorna i dati nel database
        await self.db_update(user[0], post.updated, post.link, same_link_count)

        # Costruzione messaggio (estratta in funzione separata)
        message_data = await self.build_message_data(post, user, set_telegraph)

        try:
            await self.bot.bot.send_message(
                chat_id=user[0],
                text=message_data["message"],
                parse_mode="HTML",
                reply_markup=message_data["reply_markup"],
            )
        except:
            logging.error(f"Errore invio messaggio: {e}")


async def build_message_data(self, post, user, set_telegraph):
    # Funzione unificata per la costruzione dei messaggi
    if set_telegraph:
        telegraph_link = self.safe_telegraph_transfer(post.link)
        reply_markup = make_feed_keyboard(
            "✳️Normal Link✳️", user[7], False, post.link, post.title
        )
        return {
            "message": self.format_message(
                user[7], post.title, telegraph_link, "Normal Link", post.link
            ),
            "reply_markup": reply_markup,
        }
    else:
        telegraph_link = self.safe_telegraph_transfer(post.link)
        reply_markup = make_feed_keyboard(
            "🤙Telegraph Link🤙", user[7], True, post.link, post.title
        )
        return {
            "message": self.format_message(
                user[7], post.title, post.link, "Telegraph Link", telegraph_link
            ),
            "reply_markup": reply_markup,
        }


def safe_telegraph_transfer(self, link):
    try:
        return str(webpage2telegraph.transfer(link))
    except Exception as e:
        logging.error(f"Errore generazione link Telegraph: {e}")
        return link  # Fallback al link originale


# def format_message(self, alias, title, primary_link, secondary_label, secondary_link):
#     return (
#         f"🔔{random.choice(MESSAGES_LIST)}[{alias}]\n"
#         f"--------------------------------------------------\n"
#         f"<a href='{primary_link}'>{title}</a>\n"
#         f"--------------------------------------------------\n"
#         f"<a href='{secondary_link}'>[{secondary_label}]</a>"
#     )


# Modifica la gestione dei callback
def make_feed_keyboard(name="", alias="", set_telegraph=False, link="", title=""):
    # Serializza i dati in JSON
    callback_data = {
        "option": "change_feed_link",
        "alias": alias,
        "set_telegraph": set_telegraph,
        "link": link,
        "title": title,
    }

    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(name, callback_data=callback_data)]]
    )


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


# async def update_message(
#     update,
#     context,
#     url,
#     post,
#     user,
# ):

#     if update.callback_query:
#         try:
#             data = json.loads(update.callback_query.data)
#         except json.JSONDecodeError:
#             # Gestione errore
#             pass
#     else:
#         data = {"alias": "", "link": "", "title": ""}

#     set_telegraph = data["set_telegraph"]

#     if set_telegraph:
#         reply_markup = make_feed_keyboard(
#             "✳️Normal Link✳️", data["alias"], False, data["link"], data["title"]
#         )

#         title_first = data["title"]
#         link_first = str(webpage2telegraph.transfer(data["link"]))
#         title_second = "Normal Link"
#         link_second = data["link"]
#     else:
#         reply_markup = make_feed_keyboard(
#             "🤙Telegraph Link🤙", data["alias"], True, data["link"], data["title"]
#         )

#         title_first = data["title"]
#         link_first = data["link"]
#         title_second = "Telegraph Link"
#         link_second = str(webpage2telegraph.transfer(data["link"]))

#     list = [
#         "New Update! ",
#         "Something Change in ",
#         "Here's for you, from",
#         "Drin drin! ",
#         "News FROM ",
#     ]
#     message = (
#         "🔔"
#         + random.choice(list)
#         + "["
#         + data["alias"]
#         + "] \n--------------------------------------------------\n <a href='"
#         + link_first
#         + "'>"
#         + title_first
#         + "</a>"
#         + "\n--------------------------------------------------\n<a href='"
#         + link_second
#         + "'>"
#         + "["
#         + title_second
#         + "]"
#         + "</a>"
#     )

#     try:

#         await send_check_message(update, message=message, reply_markup=reply_markup)

#     except:
#         print("dio porco")
#         # handle all other telegram related errors
#         pass


def send_feed(telegraph, alias, post_link, post_title):
    # telegraph mi dice se il link che sto inviando è in versione telegraph o no
    if telegraph:
        reply_markup = make_feed_keyboard(
            "✳️Normal Link✳️", alias, False, post_link, post_title
        )
        title_first = post_title
        # title_type = "🤙Telegram Link🤙\n "
        link_first = webpage2telegraph.transfer(post_link)
        # title_second = "Normal Link"
        # link_second = post_link
    else:
        reply_markup = make_feed_keyboard(
            "🤙Telegraph Link🤙", alias, True, post_link, post_title
        )

        # title_type = "✳️Normal Link✳️\n "
        title_first = post_title
        link_first = post_link
        # title_second = "Telegraph Link"
        # link_second = str(webpage2telegraph.transfer(post_link))

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
        + "[ "
        + alias
        + " ]"
        + " <a href='"
        + link_first
        + "'>"
        + "<blockquote>"
        + title_first
        + "</blockquote>"
        + "</a>"
        + "\n   \n"
    )

    return message, reply_markup
