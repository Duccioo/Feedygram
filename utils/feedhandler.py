import feedparser
import re
import json


class FeedHandler(object):
    @staticmethod
    def parse_feed(url, entries=0):
        """
        Parses the given url, returns a list containing all available entries
        """

        if 1 <= entries <= 10:
            feed = feedparser.parse(url)

            return feed
        else:
            feed = feedparser.parse(url)

            return feed

    @staticmethod
    def is_parsable(url):
        """
        Checks wether the given url provides a news feed. Return True if news are available, else False
        """

        # url_pattern = re.compile("((http(s?))):\/\/.*")
        # if not url_pattern.match(url):
        #     return False

        feed = feedparser.parse(url)

        # Check if result is empty
        if not feed.entries:
            print("ce qualcosa che non va")
            return False
        # Check if entries provide updated attribute
        for post in feed.entries:
            print(post)

        return True

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


feeds = FeedHandler.parse_feed("https://multiplayer.it/feed/rss/homepage/")
# feeds = FeedHandler.parse_feed("https://siliconarcadia.substack.com/feed")
# feeds = FeedHandler.parse_feed("https://feeds.feedburner.com/hd-blog")
for item in feeds.entries[:1]:
    print(item.title)
