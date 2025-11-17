import feedparser
import webpage2telegraph


class FeedHandler:
    def __init__(self, url) -> None:
        self.url = url
        if FeedHandler.is_parsable(url):
            self.feed = FeedHandler.parse_feed(url)
        else:
            self.feed = None
            print("Feed non parsabile: ", url)

    @staticmethod
    def parse_feed(url):
        url = FeedHandler.format_url_string(url)
        print("Parsing feed:", url)

        if not FeedHandler.is_parsable(url):
            return None

        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

        feed = feedparser.parse(url, agent=user_agent)
        if "title" in feed.feed:
            return feed
        else:
            return None

    @staticmethod
    def parse_N_entries(url, entries=0):
        feed = FeedHandler.parse_feed(url)
        if entries == 0:
            if feed:
                return feed.entries
            else:
                return None
        else:
            if feed:
                return feed.entries[:entries]
            else:
                return None

    @staticmethod
    def parse_first_entries(url):
        list = FeedHandler.parse_N_entries(url, 1)
        if list:
            return list[0]
        else:
            return None

    @staticmethod
    def is_parsable(url):
        """
        Checks wether the given url provides a news feed. Return True if news are available, else False
        """
        feed = feedparser.parse(url)

        if feed.bozo:
            print(f"Attenzione: Il feed potrebbe contenere errori: {feed.bozo_exception}")

        if feed.entries:
            for post in feed.entries:
                if hasattr(post, "updated"):
                    return True
            return "does not present date on the articles"
        return "does not even have articles"

    @staticmethod
    def get_feed_title(url):
        feed = feedparser.parse(url)
        try:
            return feed.feed.title
        except AttributeError:
            return None

    @staticmethod
    def format_url_string(string: str) -> str:
        """
        Formats a given url as string so it matches http(s)://adress.domain.
        This should be called before parsing the url, to make sure it is parsable
        """

        if not string.startswith(("http://", "https://")):
            string = "http://" + string
        return string

    @staticmethod
    def get_entry_id(entry) -> str:
        """
        Restituisce un identificatore univoco per un entry del feed.
        """
        if hasattr(entry, 'id') and entry.id:
            return entry.id
        if hasattr(entry, 'link') and entry.link:
            return entry.link
        # Fallback se mancano sia id che link
        title = getattr(entry, 'title', '')
        updated = getattr(entry, 'updated', '')
        return f"{title}-{updated}"


if __name__ == "__main__":

    feeds = []

    link_1 = "https://duccioo.github.io/GitHubTrendingRSS/feeds/all_languages_weekly.xml"


    feeds.append(FeedHandler.parse_feed(link_1))
    # feeds.append(FeedHandler.parse_feed("https://siliconarcadia.substack.com/feed"))
    # feeds.append(FeedHandler.parse_feed("https://multiplayer.it/feed/rss/news/"))
    # feeds.append(FeedHandler.parse_feed("https://multiplayer.it/feed/rss/articoli/"))
    # feeds.append(FeedHandler.parse_feed("https://feeds.feedburner.com/hd-blog"))

    for item in feeds:
        print(
            "Testata:",
            item.feed.title,
            "----titolo",
            item.entries[0].title,
            " in data-->",
            item.entries[0].updated,
        )
        # print(
        #     "telegraph",
        #     webpage2telegraph.transfer("https://www.behance.net/gallery/150667351/Acid-Summer-Portraits"),
        # )
