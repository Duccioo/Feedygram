import feedparser
import re
import webpage2telegraph


class FeedHandler(object):
    @staticmethod
    def parse_feed(url):

        feed = feedparser.parse(url)
        if "title" in feed.feed:
            # ok feed trovato
            return feed
        else:
            # url not parsed
            return False

    @staticmethod
    def parse_N_entries(url, entries=0):
        # return a list of entries
        feed = FeedHandler.parse_feed(url)
        if entries == 0:
            # restituisco tutti gli articoli
            if feed != False:
                return feed.entries
            else:
                return False
        else:
            if feed != False:
                return feed.entries[:entries]
            else:
                return False

    @staticmethod
    def parse_first_entries(url):
        list = FeedHandler.parse_N_entries(url, 1)
        if list != False:
            # print(list)
            return list[0]
        else:
            return False

    @staticmethod
    def is_parsable(url):
        """
        Checks wether the given url provides a news feed. Return True if news are available, else False
        """
        feed = feedparser.parse(url)

        # Check if result is empty
        try:
            if feed.entries:

                # Check if entries provide updated attribute
                for post in feed.entries:
                    try:
                        if post.updated:
                            return True
                    except:
                        return "does not present date on the articles"

        except:
            # non ho trovato nessun'articolo
            return "does not even have articles"

        return "have a problem with this url"
        # Da IMPLEMENTARE:
        # provo lo stesso a vedere se almeno tra i meta-dati compare l'aggiornamento
        # if feed.feed.updated:
        #     return "special"

    @staticmethod
    def get_feed_title(url):
        feed = feedparser.parse(url)
        if feed.feed.title:
            return feed.feed.title
        else:
            return False

    @staticmethod
    def format_url_string(string):
        """
        Formats a given url as string so it matches http(s)://adress.domain.
        This should be called before parsing the url, to make sure it is parsable
        """

        string = string.lower()

        url_pattern = re.compile("((http(s?))):\/\/.*")
        if not url_pattern.match(string):
            string = "http://" + string

        return string


if __name__ == "__main__":

    feeds = []

    feeds.append(FeedHandler.parse_feed("https://multiplayer.it/feed/rss/recensioni/"))
    feeds.append(FeedHandler.parse_feed("https://siliconarcadia.substack.com/feed"))
    feeds.append(FeedHandler.parse_feed("https://multiplayer.it/feed/rss/news/"))
    feeds.append(FeedHandler.parse_feed("https://multiplayer.it/feed/rss/articoli/"))
    feeds.append(FeedHandler.parse_feed("https://feeds.feedburner.com/hd-blog"))

    for item in feeds:
        print(
            "Testata:",
            item.feed.title,
            "----titolo",
            item.entries[0].title,
            " in data-->",
            item.entries[0].updated,
        )
        print(
            "telegraph",
            webpage2telegraph.transfer(
                "https://www.behance.net/gallery/150667351/Acid-Summer-Portraits"
            ),
        )
