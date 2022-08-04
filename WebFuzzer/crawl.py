from collections import deque
from typing import Union
import requests
from urllib.parse import urljoin, urlsplit 
import sys
from html.parser import HTMLParser
from http import HTTPStatus

import urllib.robotparser

class LinkHTMLParser(HTMLParser):
    """Parse all links found in a HTML page"""

    def reset(self):
        super().reset()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = {attr_name: attr_value for attr_name, attr_value in attrs}

        if tag == "a" and "href" in attributes:
            # print("Found:", tag, attributes)
            self.links.append(attributes["href"])

def crawl(url, max_pages: Union[int, float] = 1, same_host: bool = True):
    """Return the list of linked URLs from the given URL.
    `max_pages` - the maximum number of pages accessed.
    `same_host` - if True (default), stay on the same host"""

    pages = deque([(url, "<param>")])
    urls_seen = set()

    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(url, "/robots.txt"))
    rp.read()

    while len(pages) > 0 and max_pages > 0:
        page, referrer = pages.popleft()
        if not rp.can_fetch("*", page):
            # Disallowed by robots.txt
            continue

        r = requests.get(page)
        max_pages -= 1

        if r.status_code != HTTPStatus.OK:
            print("Error " + repr(r.status_code) + ": " + page,
                  "(referenced from " + referrer + ")",
                  file=sys.stderr)
            continue

        content_type = r.headers["content-type"]
        if not content_type.startswith("text/html"):
            continue

        parser = LinkHTMLParser()
        parser.feed(r.text)

        for link in parser.links:
            target_url = urljoin(page, link)
            if same_host and urlsplit(
                    target_url).hostname != urlsplit(url).hostname:
                # Different host
                continue

            if urlsplit(target_url).fragment != "":
                # Ignore #fragments
                continue

            if target_url not in urls_seen:
                pages.append((target_url, page))
                urls_seen.add(target_url)
                yield target_url

        if page not in urls_seen:
            urls_seen.add(page)
            yield page