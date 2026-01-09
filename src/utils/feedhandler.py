import feedparser
import webpage2telegraph
from bs4 import BeautifulSoup
from urllib.parse import urlparse


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
    def is_parsable(url: str) -> tuple[bool, str | None]:
        """
        Verifica se l'URL fornito è un feed RSS analizzabile.

        Restituisce una tupla: (True/False, messaggio_di_errore_o_None).
        """
        feed = feedparser.parse(url)

        if feed.bozo:
            error_message = f"Errore nel parsing del feed: {feed.bozo_exception}"
            print(error_message)
            return False, error_message

        if not feed.entries:
            return False, "Il feed non contiene articoli (entries)."

        # Opzionale: verifica la presenza di campi essenziali
        for entry in feed.entries:
            if not hasattr(entry, 'title') or not hasattr(entry, 'link'):
                return False, "Alcuni articoli nel feed non hanno titolo o link."

        return True, None

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

    @staticmethod
    def extract_source_link(entry) -> str | None:
        """
        Tenta di estrarre un link alla fonte originale dalla descrizione/summary dell'entry,
        utile per feed aggregatori come Kagi che usano link proxy.
        """
        description = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
        if not description:
            return None

        try:
            soup = BeautifulSoup(description, 'html.parser')
            # Trova tutti i link nella descrizione
            links = soup.find_all('a', href=True)

            for link in links:
                href = link['href']
                parsed_url = urlparse(href)

                # Filtra link interni o non rilevanti (adattare in base alle necessità)
                if not parsed_url.netloc:
                    continue

                # Ignora link che puntano a Kagi stesso (dominio del feed proxy)
                if "kagi.com" in parsed_url.netloc:
                    continue

                # Se troviamo un link valido che non è Kagi, lo consideriamo la fonte
                # Spesso aggregatori mettono la fonte in un link testuale come (The Guardian)
                return href

        except Exception as e:
            print(f"Error extracting source link: {e}")
            return None

        return None


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
