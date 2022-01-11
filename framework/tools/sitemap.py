from typing import List, Optional
from urllib.error import HTTPError
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup
from selenium import webdriver

from framework.tools import crawler
from web_interface.apps.task.models import SitemapTask


class SiteMap:
    def __init__(self, url, mode, options=None, depth_level: Optional[int] = None):
        self.url = url
        self.mode = mode
        self.options = options
        self.sitemap = []
        self.depth_level = depth_level
        self.status = SitemapTask.FINISHED
        self.message = ""
        self.driver = webdriver.Firefox()

    def get_sitemap(self) -> List[dict]:
        self._get_pages()

        if self.status == SitemapTask.FINISHED:
            self.message = f"Depth {self.depth_level} sitemap processed, {len(self.sitemap)} pages created"
        return self.sitemap

    def _get_pages(self) -> None:
        if self.mode:
            self._get_simple_map()
        else:
            self._get_official_sitemap()

    def _get_simple_map(self) -> None:
        crawl = crawler.Crawler(url=self.url.rstrip("/"), options=self.options, depth_level=self.depth_level)
        if self.mode == "auth":
            crawl.auth()
        crawl.crawl()
        if len(crawl.errors) > 0:
            largest_error_group = None
            total_error_count = 0
            for error in crawl.errors.keys():
                total_error_count += len(crawl.errors[error])
                if largest_error_group is None or len(crawl.errors[error]) > len(
                    crawl.errors[largest_error_group]
                ):
                    largest_error_group = error

            self.status = SitemapTask.FINISHED_WITH_PROBLEMS
            self.message = f"Depth {self.depth_level} sitemap finished, but {total_error_count} pages could not be processed, {len(crawl.errors[largest_error_group])} of these pages returned a {largest_error_group} code"
            if len(crawl.hierarchy) == 1:
                self.status = SitemapTask.FAILED
                self.message = f"Depth {self.depth_level} sitemap failed, root page returned {largest_error_group}"
        self.sitemap = crawl.hierarchy

    def _get_official_sitemap(self) -> None:
        r = requests.get(self.url + "sitemap.xml")
        xml = r.text
        soup = BeautifulSoup(xml)
        sitemap_tags = soup.find_all("loc")
        print(len(sitemap_tags))
        count = 0
        for sitemap in sitemap_tags:
            count = count + 1
            print("Testing " + f"\r {count}/{len(sitemap_tags)}", end="", flush=True)
            try:
                soup = BeautifulSoup(urlopen(sitemap.text), features="lxml")
                self.sitemap.append({"url": sitemap.text, "title": soup.title.string, "parent": None})
            except HTTPError:
                pass
