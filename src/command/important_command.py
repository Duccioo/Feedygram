


async def add(self, update, context):
        # Adds a rss subscription to user

        telegram_user = update.message.from_user
        args = update.message.text.split()
        list = [
            "🍕Best site for cooking Pizza🍕",
            "🍷Best Site for sciacquare una bottiglia di Brunello",
            "🐶BauBau",
            "😏HotSite.com",
            "💩.it",
            "😴generic_news_boooring_site🥱",
            "🎮Games&Caipiroska🍹",
        ]
        if len(args) < 2:
            message = (
                "Oh nono! I could not add the entry😯!\n"
                + bip_bop()
                + "I need <b>at least</b> a valid URL, and, if you want, a custom name.\n"
                + "Try to send a valid URL like this:"
                + "\n\n"
                + "<code>/add https://duccio.me/ "
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        arg_url = FeedHandler.format_url_string(string=args[1])
        print(arg_url)
        # Check if argument matches url format
        is_parsable = FeedHandler.is_parsable(url=arg_url)
        if is_parsable != True:
            message = (
                bip_bop()
                + "Sorry! It seems like <code>"
                + str(arg_url)
                + "</code> "
                + str(is_parsable)
                + "...😣.\n Have you tried other URLs?\n"
                + "Try to send a valid URL like this:\n"
                + "<code>/add https://duccio.me/ "
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        # Check if entry does not exists
        entries = self.db.get_urls_for_user(telegram_id=telegram_user.id)

        if any(arg_url.lower() in entry for entry in entries):
            message = (
                "Sorry, "
                + telegram_user.first_name
                + "!I already have that url with stored in your subscriptions😒"
                + "\nAdd a new one like this:\n"
                + "<code>/add https://duccio.me/ "
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        if len(args) == 2:
            arg_entry = (
                random_emoji()
                + " "
                + FeedHandler.get_feed_title(arg_url)
                + " "
                + random_emoji()
            )
            if arg_entry == False:
                message = (
                    bip_bop()
                    + "mhh... I tried my best for create a title for that url but I can't...\n"
                    + telegram_user.username
                    + "try to resend <code> /add "
                    + args[1]
                    + "</code> and this time add a costum name!"
                    + bip_bop()
                    + "\nLike this: "
                    + "<code>/add https://duccio.me/ "
                    + random.choice(list)
                    + "</code>"
                )
                await update.message.reply_text(
                    message,
                    parse_mode="HTML",
                )

        elif len(args) >= 3:
            arg_entry = ""
            for i in range(3, len(args)):
                arg_entry = arg_entry + " " + args[i]
        list1 = ["I'm stressed...😣", "I'm bored... 🥱", "I'm in love...🥰"]
        if any(arg_entry in entry for entry in entries):
            message = (
                "🤬<b>NOOOO!\nI ALREADY HAVE AN ENTRY WITH THAT NAMEEE!!"
                + bip_bop()
                + "</b>\n\n...\n\nSorry 😥, "
                + random.choice(list1)
                + "\nTry to send my another feed like this:\n"
                + "<code>/add https://duccio.me/ "
                + random.choice(list)
                + "</code>"
            )
            await update.message.reply_text(
                message,
                parse_mode="HTML",
            )
            return

        self.db.add_user_bookmark(
            telegram_id=telegram_user.id, url=arg_url.lower(), alias=arg_entry
        )
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔗Change to Telegraph Link🔗",
                    callback_data={
                        "option": "change_database",
                        "alias": arg_entry,
                        "url": arg_url.lower(),
                    },
                )
            ],
        ]
        message = (
            "WOOW!!🤝"
            + bip_bop()
            + "\nI successfully added "
            + arg_entry
            + " to your subscriptions!"
            + bip_bop()
            + "\n👀Look! By default when I found a new post I try to send <b>Normal Link</b>.\n"
            + "If you want to always receive <b>Telegraph Link</b> (to open with <u>Instant View</u>) click the button below"
        )
        await update.message.reply_text(
            text=message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def get(self, update, context):
    """
    Manually parses an rss feed
    """

    telegram_user = update.message.from_user
    args = update.message.text.split()

    if len(args) > 3 or len(args) <= 1:
        message = "To get the last news of your subscription please use /get <entryname> [optional: <count 1-10>]. Make sure you first add a feed using the /add command."
        await update.message.reply_text(message)
        return

    if len(args) == 3:
        args_entry = args[1].lower()
        args_count = int(args[2])
    else:
        args_entry = args[1]
        args_count = 1

    url = self.db.get_user_bookmark(telegram_id=telegram_user.id, alias=args_entry)

    if url is None:
        message = (
            "I can not find an entry with label "
            + args_entry
            + " in your subscriptions! Please check your subscriptions using /list and use the delete command again!"
        )
        await update.message.reply_text(message)
        return

    entries = FeedHandler.parse_feed(url[0], args_count)
    for entry in entries.entries[:args_count]:
        message = (
            "["
            + url[1]
            + "] <a href='"
            + entry.link
            + "'>"
            + entry.title
            + str(entries.feed.updated)
            + "</a>"
        )

        try:
            await update.message.reply_text(message, parse_mode="HTML")

        except:
            print("errore")
            # handle all other telegram related errors
            pass

async def remove(self, update, context):
    """
    Removes an rss subscription from user
    """

    args = context.args

    telegram_user = update.message.from_user

    if len(args) < 1:
        message = "To remove a subscriptions from your list please use /remove <entryname>. To see all your subscriptions along with their entry names use /list !"
        await update.message.reply_text(message)
        return

    entry_args = (" ").join(args[0:])
    print(entry_args)

    entry = self.db.get_user_bookmark(
        telegram_id=telegram_user.id, alias=entry_args
    )

    if entry:
        self.db.remove_user_bookmark(telegram_id=telegram_user.id, url=entry[0])
        message = (
            "Mhh..."
            + bip_bop()
            + "OK, I removed "
            + entry_args
            + " from your subscriptions!"
        )
        await update.message.reply_text(message)
    else:
        message = (
            "I can not find an entry with label "
            + args[0]
            + " in your subscriptions! Please check your subscriptions using /list and use the delete command again!"
        )
        await update.message.reply_text(message)
