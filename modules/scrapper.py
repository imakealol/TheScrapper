from typing import Any
import requests
from requests.models import Response
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Shared session for connection pooling and default headers
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; TheScrapper/1.0; +https://github.com/AhmadShahzad/TheScrapper)"
})


class Scrapper:
    """
    Scrapper Class
    """

    def __init__(self, url: str = None, contents: list = [], crawl: int = 0, crawl_external: bool = False) -> None:
        """Contructor

        Args:
            url (str): [description]. Defaults to None.
            contents (list, optional): Defaults to [].
            crawl (int): Max number of discovered URLs to crawl. 0 disables crawling.
            crawl_external (bool): Include external URLs while crawling.
        """

        self.url = url
        self.urls = []
        self.contents = contents
        self.crawl = max(0, int(crawl or 0))
        self.crawl_external = crawl_external
        self._page_text = None

    def _is_internal_url(self, url: str) -> bool:
        if not self.url:
            return False
        base_host = urlparse(self.url).netloc.lower()
        target_host = urlparse(url).netloc.lower()
        return base_host == target_host

    def clean(self) -> list:
        """clean function

        Returns:
            list: [description]
        """

        contents: list = []

        for content in self.contents:
            soup: any = BeautifulSoup(content, "html.parser")

            for script in soup(["script", "style"]):
                script.extract()

            cleaned: str = soup.get_text()
            lines: object = (line.strip() for line in cleaned.splitlines())
            chunks: object = (
                phrase.strip()
                for line in lines for phrase in line.split("  ")
            )
            contents.append('\n'.join(chunk for chunk in chunks if chunk))

        return contents

    def _fetch(self) -> str | None:
        """Fetch the page once and cache the result."""
        if self._page_text is None:
            try:
                self._page_text = _session.get(self.url, timeout=15).text
            except requests.exceptions.RequestException:
                self._page_text = ""
        return self._page_text or None

    def getURLs(self) -> list:
        """getURLs function

        Returns:
            list: [description]
        """

        urls: list = []
        content = self._fetch()
        if content is None:
            return urls
        soup = BeautifulSoup(content, "html.parser")
        for link in soup.find_all('a'):
            if link.get("href") is not None:
                if self.url not in link.get("href"):
                    if "http" not in link.get("href") and "https" not in link.get("href") and "mailto:" not in link.get(
                            "href"):
                        urls.append(self.url + link.get('href'))
                        continue
            urls.append(link.get("href"))
        return urls

    def getText(self) -> dict:
        """getText function

        Returns:
            dict
        """
        urls = self.getURLs()
        contents: list = []
        if self.crawl > 0:
            fetched = 0
            for url in urls:
                if fetched >= self.crawl:
                    break
                try:
                    if url is not None and url.startswith(("http://", "https://")):
                        if not self.crawl_external and not self._is_internal_url(url):
                            continue
                        req: Response = _session.get(url, timeout=15)
                        contents.append(req.text)
                        fetched += 1
                except requests.exceptions.RequestException:
                    pass
        else:
            page = self._fetch()
            if page:
                contents.append(page)
        contents = Scrapper(contents=contents).clean()
        return {"text": contents, "urls": urls}
