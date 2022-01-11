from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from urllib.parse import urlparse


def get_children(element, driver, target_tag=''):
    if element is None:
        return []
    try:
        if target_tag:
            return element.find_by_xpath("child::" + target_tag, driver)
        return element.find_by_xpath("child::*", driver)
    except (StaleElementReferenceException, NoSuchElementException):
        return []


def find_logo_link(driver, links, url):
    """looking for a logo image that is a link to the main page"""

    for link in links:
        children = get_children(link, driver)
        if len(children) == 1 and children[0].tag_name == 'img':
            href = link.get_attribute(driver, "href")
            if href is None:
                continue
            if href == "/":
                return link

            parsed_url = urlparse(href)
            parsed_original_url = urlparse(url)
            # Link uses 'javascript:' pseudo-protocol
            if parsed_url.scheme == "javascript":
                continue

            # The link leads to a third-party resource - not a navigation tool on the page
            original_url_set = set(parsed_original_url.netloc.split('.'))
            url_set = set(parsed_url.netloc.split('.'))

            if len(original_url_set & url_set) != len(url_set):
                return

            # check that this is a link to the main page
            if (href == "{}://{}/".format(href[:href.find(":")], min(parsed_original_url.netloc, parsed_url.netloc))
                    or href == "{}://{}".format(href[:href.find(":")],
                                                min(parsed_original_url.netloc, parsed_url.netloc))):
                return link
