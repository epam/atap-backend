from selenium import webdriver
from urllib.parse import urlparse
import re
from framework.element_locator import ElementLocator
from framework.element import Element


name = "Ensures that <a> elements have appropriate 'role' attributes"

locator_required_elements = []
framework_version = 0
WCAG = "4.1.2"
elements_type = "link"
test_data = [
    {
        "page_info": {
            "url": "links/page_fake_links_ok.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links/page_fake_links_fail.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    }
]


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):

    activity.get(webdriver_instance)

    links = ElementLocator.get_all_of_type(webdriver_instance, ["a"])

    if len(links) == 0:
        return {
            "status": "NOELEMENTS",
            "message": "There are no links on the page"
        }

    fake_links = list()

    counter = 0

    href_regex = re.compile(r'''<a [^>]*href="([^"]*)"''')

    def check_link(link_element):
        nonlocal counter
        link = link_element.get_element(webdriver_instance)
        counter += 1
        print(f"\rChecking link {counter}/{len(links)}", end="")

        if not link.is_displayed():
            return

        # If this link has a special role - ignore
        if link.get_attribute("role") is not None:
            return
        # If this is a dropdown - ignore
        if link.get_attribute("aria-haspopup") == "true":
            return

        href = link.get_attribute("href")
        if href is None:
            fake_links.append({
                "element": Element(link, webdriver_instance),
                "problem": "Link has no href"
            })
            return
        parsed_url = urlparse(href)
        if parsed_url.scheme == "javascript":
            fake_links.append({
                "element": Element(link, webdriver_instance),
                "problem": "Link uses 'javascript:' pseudo-protocol"
            })
            return

        href_match = href_regex.match(link.get_attribute("outerHTML"))
        if href_match is not None and href_match.group(1) == "#":
            fake_links.append({
                "element": Element(link, webdriver_instance),
                "problem": "Link has '#' as its href"
            })
            return

    Element.safe_foreach(links, check_link)

    print()
    if len(fake_links) > 0:
        return {
            "status": "FAIL",
            "message": f"Found {len(fake_links)} fake links",
            "elements": fake_links,
            "checked_elements": links
        }
    return {
        "status": "PASS",
        "message": "No fake links found",
        "checked_elements": links
    }
