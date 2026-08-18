import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import Optional, Tuple, List, Any


class FeedHandler:
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    def __init__(self, url: str) -> None:
        self.url = self.format_url_string(url)
        self.feed = self.parse_feed(self.url)

    @staticmethod
    def format_url_string(string: str) -> str:
        """
        Formats a given url as string so it matches http(s)://address.domain.
        """
        string = string.strip()
        if not string.startswith(("http://", "https://")):
            string = "https://" + string
        return string

    @classmethod
    def parse_feed(cls, url: str) -> Optional[Any]:
        url = cls.format_url_string(url)
        try:
            feed = feedparser.parse(url, agent=cls.USER_AGENT)
            if hasattr(feed, "feed") and (getattr(feed.feed, "title", None) or len(feed.entries) > 0):
                return feed
            return None
        except Exception as e:
            print(f"Errore durante il parsing del feed {url}: {e}")
            return None

    @classmethod
    def parse_N_entries(cls, url: str, entries: int = 0) -> Optional[List[Any]]:
        feed = cls.parse_feed(url)
        if not feed:
            return None

        # Se entries <= 0 (es. 0 o -1), restituisce tutti gli articoli disponibili
        if entries <= 0:
            return list(feed.entries)
        return list(feed.entries[:entries])

    @classmethod
    def parse_first_entries(cls, url: str) -> Optional[Any]:
        entries_list = cls.parse_N_entries(url, 1)
        if entries_list and len(entries_list) > 0:
            return entries_list[0]
        return None

    @classmethod
    def is_parsable(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se l'URL fornito è un feed RSS analizzabile.
        Restituisce una tupla: (True/False, messaggio_di_errore_o_None).
        """
        url = cls.format_url_string(url)
        try:
            feed = feedparser.parse(url, agent=cls.USER_AGENT)
        except Exception as e:
            return False, f"Impossibile raggiungere il feed: {e}"

        # Se feed.entries contiene elementi, il feed è valido anche se ci sono warning XML minori (bozo=1)
        if hasattr(feed, "entries") and len(feed.entries) > 0:
            return True, None

        if feed.bozo and hasattr(feed, "bozo_exception"):
            return False, f"Errore nel formato del feed: {feed.bozo_exception}"

        if not hasattr(feed, "entries") or len(feed.entries) == 0:
            return False, "Il feed non contiene articoli (entries)."

        return True, None

    @classmethod
    def discover_feed_url(cls, url: str) -> Optional[str]:
        """
        Rileva automaticamente l'endpoint RSS/Atom/JSON a partire da un generico URL web.
        """
        formatted = cls.format_url_string(url)
        is_ok, _ = cls.is_parsable(formatted)
        if is_ok:
            return formatted

        try:
            import requests
            from urllib.parse import urljoin

            headers = {"User-Agent": cls.USER_AGENT}
            resp = requests.get(formatted, headers=headers, timeout=5)
            if resp.status_code != 200 or not resp.text:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. Cerca link rel="alternate" nel tag <head>
            feed_types = {
                "application/rss+xml",
                "application/atom+xml",
                "application/json",
                "application/xml",
                "text/xml",
            }
            for link in soup.find_all("link", rel=lambda r: r and "alternate" in str(r).lower()):
                t = link.get("type", "").lower()
                href = link.get("href")
                if href and (t in feed_types or "rss" in href.lower() or "feed" in href.lower() or "atom" in href.lower()):
                    candidate = urljoin(formatted, href)
                    cand_ok, _ = cls.is_parsable(candidate)
                    if cand_ok:
                        return candidate

            # 2. Cerca link comuni nell'HTML
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if any(href.lower().endswith(ext) for ext in (".rss", ".atom", "/feed", "/rss", "/rss.xml", "/feed.xml")):
                    candidate = urljoin(formatted, href)
                    cand_ok, _ = cls.is_parsable(candidate)
                    if cand_ok:
                        return candidate

            # 3. Tentativi su percorsi standard
            for common_path in ("/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml", "/index.xml"):
                candidate = urljoin(formatted, common_path)
                cand_ok, _ = cls.is_parsable(candidate)
                if cand_ok:
                    return candidate

        except Exception:
            pass

        return None

    @classmethod
    def get_feed_title(cls, url: str) -> Optional[str]:
        feed = cls.parse_feed(url)
        if feed and hasattr(feed, "feed") and getattr(feed.feed, "title", None):
            return feed.feed.title
        return None

    @staticmethod
    def get_entry_id(entry: Any) -> str:
        """
        Restituisce un identificatore univoco e consistente per un entry del feed.
        """
        # 1. Prova l'ID / GUID esplicito
        entry_id = getattr(entry, "id", None) or getattr(entry, "guid", None)
        if entry_id and str(entry_id).strip():
            return str(entry_id).strip()

        # 2. Prova il link
        link = getattr(entry, "link", None)
        if link and str(link).strip():
            return str(link).strip()

        # 3. Fallback deterministico su titolo + data
        title = getattr(entry, "title", "")
        date = (
            getattr(entry, "published", "")
            or getattr(entry, "updated", "")
            or ""
        )
        return f"{title}_{date}".strip()

    @staticmethod
    def extract_source_link(entry: Any) -> Optional[str]:
        """
        Tenta di estrarre un link alla fonte originale se l'entry proviene da un aggregatore proxy come Kagi.
        In caso contrario restituisce il link principale dell'entry.
        """
        link = getattr(entry, "link", None)
        if link and "kagi.com" not in link:
            return link

        description = getattr(entry, "summary", "") or getattr(entry, "description", "")
        if not description:
            return link

        try:
            soup = BeautifulSoup(description, "html.parser")
            links = soup.find_all("a", href=True)
            for l in links:
                href = l["href"]
                parsed_url = urlparse(href)
                if parsed_url.netloc and "kagi.com" not in parsed_url.netloc:
                    return href
        except Exception:
            pass

        return link


if __name__ == "__main__":
    link_1 = "https://duccioo.github.io/GitHubTrendingRSS/feeds/all_languages_weekly.xml"
    feed = FeedHandler.parse_feed(link_1)
    if feed and feed.entries:
        print("Testata:", getattr(feed.feed, "title", "No Title"))
        print("Primo articolo ID:", FeedHandler.get_entry_id(feed.entries[0]))

