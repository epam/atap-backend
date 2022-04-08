from time import sleep

import re
from typing import Optional
from urllib.parse import urljoin

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from lxml import html
from selenium import webdriver

from framework.await_page_load import wait_for_page_load
from framework.activity import auth_by_options

FORBIDDEN_TOP_LEVEL_REGEX = re.compile(r"\.(htm|html|php)\?.*$")


class Crawler:
    def __init__(self, url: str, options: Optional[str] = None, depth_level=1):
        self.webdriver_instance = webdriver.Firefox(firefox_profile=self._firefox_profile)
        self.url = url

        self.depth_level = depth_level

        # create lists for urls in queue and visited urls
        self.urls = {url}
        self.visited = {url}
        self.hierarchy = []
        self.checked = []
        self.errors = {}
        self.options = options

    @property
    def _firefox_profile(self):
        profile = webdriver.FirefoxProfile()
        # 1 - Allow all images
        # 2 - Block all images
        # 3 - Block 3rd party images
        profile.set_preference("permissions.default.image", 2)
        return profile

    def crawl(self) -> None:
        print("Parsing pages")
        parse_runs = 0
        parsed_urls = self.urls.copy()

        for url in parsed_urls:
            self.hierarchy.append({"url": url, "parent": None})
        while len(parsed_urls) > 0 and self.depth_level > parse_runs:
            print(f"Processing depth level {parse_runs + 1}")
            parsed_urls = self._parse(parsed_urls)
            parse_runs += 1
            print(f"Depth level processed {parse_runs}")
        for item in self.hierarchy:
            print(item)
        self.webdriver_instance.quit()

    def auth(self):
        self.webdriver_instance.get(self.url)

        try:
            auth_by_options(self.webdriver_instance, self.options)
        except Exception as e:
            # TODO cancel sitemap
            print(f"Crawler Exception during authentication {e}")
            self.errors["auth"] = [f"Auth Failed: {e}"]
            wait_for_page_load(self.webdriver_instance)

    def _wait_loading(self, loading_timeout=10):
        driver = self.webdriver_instance
        # already finished waiting in get method
        # wait_for_page_load(driver)  # awaiting for all resources on page
        wait_time = 0
        href_script = 'return Array.from(document.getElementsByTagName("a")).map(element => element.href);'
        ready_script = "return document.readyState;"

        while (
            driver.execute_script(ready_script) != "complete" or not driver.execute_script(href_script)
        ) and wait_time < loading_timeout:
            wait_time += 0.1
            sleep(0.1)

    def _parse(self, urls):
        parsed_urls = set()

        for url in urls or ():
            try:
                print(f"Sending request to {url}...")
                try:
                    user_agent = self.webdriver_instance.execute_script("return navigator.userAgent;")
                    headers, verify, get_req_timeout = {"User-Agent": user_agent}, False, 10

                    response = requests.get(url, headers=headers, verify=verify, timeout=get_req_timeout)
                except requests.Timeout:
                    print("Request timed out!")
                    if 408 not in self.errors:
                        self.errors[408] = []
                    self.errors[408].append(url)
                    continue

                print(f"GOT CODE {response.status_code}")
                if response.status_code == 400 or response.status_code > 401:
                    # ignore 401 Unauthorized - can't swiftly authenticate with requests
                    print(f"Url check failed: error code {response.status_code} returned")
                    if response.status_code not in self.errors:
                        self.errors[response.status_code] = []
                    self.errors[response.status_code].append(url)
                    continue

                self.webdriver_instance.get(url)
                print(f'Waiting for page load : "{url}"')
                self._wait_loading()

                try:
                    source = self.webdriver_instance.page_source
                    tree = html.fromstring(source)
                except ValueError as e:
                    print(e)
                    response = requests.get(url, headers=headers, verify=verify, timeout=get_req_timeout)
                    tree = html.fromstring(response.text)

                tag_xpath = "//a"
                onclick_attr_xpath = (
                    "//*[starts-with(@onclick,  'location') or starts-with(@onclick, 'window.open')]"
                )

                for link_tag in tree.xpath(f"{tag_xpath} | {onclick_attr_xpath}"):
                    link_address = link_tag.attrib.get("href", "")
                    newurl = urljoin(self.url, link_address)

                    if self._is_valid(newurl):
                        self.visited.update([newurl])
                        self.urls.update([newurl])
                        parsed_urls.update([newurl])
                        self.hierarchy.append({"url": newurl, "parent": url})
            except Exception as e:
                print(f"General exception {e}")

        return parsed_urls

    def _is_valid(self, url: str) -> bool:
        # * ignore schemes mailto, tel, ftp, nntp...
        if not url.startswith("http"):
            return False

        if url[-1] == "/":
            slash_url, without_slash_url = url, url[:-1]
        else:
            slash_url, without_slash_url = f"{url}/", url

        # * ignore hyperlink anchor, still the url can contain external link
        if "#" in url:
            anchor_id = url.find("#")
            slash_url, without_slash_url = slash_url[:anchor_id], without_slash_url[:anchor_id]

        # * check dup
        if any(loc in self.visited for loc in [url, without_slash_url, slash_url]):
            return False

        # * verify service.site.com is part of site.com
        # * self.url is main page url
        if self.url not in url:
            s_domain = re.search("https?://([A-Za-z_0-9.-]+).*", self.url).group(1).split(".")
            if len(s_domain) < 2:
                return False
            domain = f"{s_domain[-2]}.{s_domain[-1]}"  # mdbootstrap.com

            if domain not in url:
                return False

        return not re.search(FORBIDDEN_TOP_LEVEL_REGEX, url)
