import re
import time
from urllib.parse import urljoin

import requests
from lxml import html
from selenium import webdriver

from framework.await_page_load import wait_for_page_load
from framework.activity import auth_by_options

ALLOWED_REGEX = re.compile("\.((?!htm)(?!html)(?!php)\w+)$")


class Crawler:
    LOADING_TIMEOUT = 8

    def __init__(self, url, options=None, depth_level=1):
        self.webdriver_instance = webdriver.Firefox(firefox_profile=self.firefox_profile)
        self.url = url

        self.depth_level = depth_level or 1

        # create lists for urls in queue and visited urls
        self.urls = {url}
        self.visited = {url}
        self.hierarchy = []
        self.checked = []
        self.errors = {}
        self.options = options

    @property
    def firefox_profile(self):
        profile = webdriver.FirefoxProfile()
        # 1 - Allow all images
        # 2 - Block all images
        # 3 - Block 3rd party images
        profile.set_preference("permissions.default.image", 2)
        return profile

    def crawl(self):
        print("Parsing pages")
        parse_runs = 0
        parsed_urls = self.urls.copy()

        for url in parsed_urls:
            self.hierarchy.append({"url": url, "parent": None})
        while len(parsed_urls) > 0 and self.depth_level > parse_runs:
            print(f"Processing depth level {parse_runs + 1}")
            parsed_urls = self.parse(parsed_urls)
            parse_runs += 1
            print(f"Depth level processed {parse_runs}")
        for item in self.hierarchy:
            print(item)
        self.webdriver_instance.quit()

    def wait_loading(self):
        driver = self.webdriver_instance
        wait_for_page_load(driver)  # awaiting for all resources on page
        wait_time = 0
        href_script = 'return Array.from(document.getElementsByTagName("a")).map(element => element.href);'
        ready_script = "return document.readyState;"
        while (
            driver.execute_script(ready_script) != "complete" or not driver.execute_script(href_script)
        ) and wait_time < self.LOADING_TIMEOUT:
            # Scroll down to bottom to load contents, unnecessary for everyone
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            wait_time += 0.1
            time.sleep(0.1)

    def parse(self, urls):
        parsed_urls = set()
        for url in urls or ():
            try:
                print(f"Sending request to {url}...")
                try:
                    response = requests.head(url=url, allow_redirects=True, timeout=10)
                except requests.Timeout:
                    print("Request timed out!")
                    if 408 not in self.errors:
                        self.errors[408] = []
                    self.errors[408].append(url)
                    continue

                print(f"GOT CODE {response.status_code}")
                if 400 <= response.status_code > 401:
                    # ignore 401 Unauthorized - can't swiftly authenticate with requests
                    print(f"Url check failed: error code {response.status_code} returned")
                    if response.status_code not in self.errors:
                        self.errors[response.status_code] = []
                    self.errors[response.status_code].append(url)
                    continue

                self.webdriver_instance.get(url)
                print(f'Waiting for page load : "{url}"')
                self.wait_loading()

                try:
                    source = self.webdriver_instance.page_source
                    tree = html.fromstring(source)
                except ValueError as e:
                    print(e)
                    response = requests.get(url=url)
                    tree = html.fromstring(response.text)
                for link_tag in tree.findall(".//a"):
                    link = link_tag.attrib.get("href", "")
                    newurl = urljoin(self.url, link)
                    if self.is_valid(newurl):
                        self.visited.update([newurl])
                        self.urls.update([newurl])
                        parsed_urls.update([newurl])
                        self.hierarchy.append({"url": newurl, "parent": url})

            except Exception as e:
                print(e)

        return parsed_urls

    def is_valid(self, url):
        oldurl = url
        without_slash_url = url
        slash_url = url
        if url[-1] == "/":
            without_slash_url = without_slash_url[:-1]
        else:
            slash_url = url + "/"
        if "#" in url:
            url = url[: url.find("#")]
        if (
            url in self.visited
            or oldurl in self.visited
            or without_slash_url in self.visited
            or slash_url in self.visited
        ):
            return False
        if self.url not in url:
            s_domain = re.search("https?://([A-Za-z_0-9.-]+).*", self.url).group(1).split(".")
            if len(s_domain) <= 2:
                return False
            domain = f"{s_domain[-2]}.{s_domain[-1]}"
            if domain not in url:
                return False
        return not re.search(ALLOWED_REGEX, url)

    def auth(self):
        self.webdriver_instance.get(self.url)
        wait_for_page_load(self.webdriver_instance)

        try:
            auth_by_options(self.webdriver_instance, self.options)
        except Exception as e:
            # TODO cancel sitemap
            print(f"Crawler Exception during authentication {e}")
            self.errors["auth"] = [f"Auth Failed: {e}"]
        else:
            wait_for_page_load(self.webdriver_instance)
