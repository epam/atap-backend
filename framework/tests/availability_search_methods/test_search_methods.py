import re
from urllib.parse import urlparse, ParseResult
import tempfile
from typing import List, Pattern

from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tools.sitemap import SiteMap
from framework.activity import Activity
from framework.libs.is_visible import is_visible

framework_version = 5
WCAG = '2.4.5'
webdriver_restart_required = False
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "search_methods/page_bad_search_methods.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "search_methods/page_bad_search_methods_2.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "search_methods/page_good_search_methods.html"
        },
        "expected_status": "PASS"
    }
]


name = 'Ensures that web page has several ways to navigate'
locator_required_elements = []


WORD_LIST = ['find', 'search', 'nav', 'menu', 'site map', 'sitemap', 'catalog', 'content', 'найдите']


def get_children(element: Element, driver: webdriver.Firefox, target_tag: str = '*') -> List[Element]:
    """
    get child elements with a specific tag
    :param element:
    :param driver:
    :param target_tag:
    :return:
    """
    return element.safe_operation_wrapper(lambda x: x.find_by_xpath(f"child::{target_tag}", driver), on_lost=lambda: [])


def find_loup_near_elem(driver: webdriver.Firefox, element: Element) -> bool:
    """
    looking for element loup in the parent element and on a level above parent
    :param driver:
    :param element:
    :return:
    """
    def find(elem: Element) -> bool:
        parent = elem.get_parent(driver)
        buttons = parent.find_by_xpath("child::*[self::input[@type='image'] or self::button]", driver)
        if not buttons:
            buttons.extend(get_children(parent.get_parent(driver), driver, 'button'))
        return any([any([button.source.lower().find(word) != -1 for word in WORD_LIST]) for button in buttons])
    return element.safe_operation_wrapper(find, on_lost=lambda: False)


def find_search_input_area(driver: webdriver.Firefox, elements: List[Element]) -> bool:
    """
    Search for input fields to search the site
    :param driver:
    :param elements: input fiend with type='text' or type='search'
    :return:
    """
    # looking for words related to the search, in the item description
    if any([any([elem.source.lower().find(word) != -1 for word in WORD_LIST]) for elem in elements]):
        return True
    # otherwise, try to find the loupe button next to the field
    return any([find_loup_near_elem(driver, elem) for elem in elements])


def get_list_header(driver: webdriver.Firefox, element: Element) -> str:
    """
    get the header at the top of the submitted item
    :param driver:
    :param element:
    :return:
    """
    def get(elem: Element):
        children = get_children(elem.get_parent(driver), driver)
        for child1, child2 in zip(children, children[1:]):
            if child2 == elem and (child1.tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'p']):
                return child1.get_text(driver)
        return ""
    return element.safe_operation_wrapper(get, on_lost=lambda: "")


def find_page_in_links_list(driver: webdriver.Firefox, navigation_links: List[Element], links: List[Element],
                            page: ParseResult, check_grid: bool, href_regex: Pattern) -> bool:
    """
    find a link to a page from the site map in the list of links
    :param driver:
    :param navigation_links: list of web elements with the <a> tag
    :param links: list of web elements with the <a> tag
    :param page:
    :param check_grid: flag to check that the link contains '#' in the href attribute
    :param href_regex:
    :return:
    """
    for link in links:
        href = link.get_attribute(driver, "href")
        if href is None:
            continue
        parsed_url = urlparse(href)
        # Link uses 'javascript:' pseudo-protocol
        if parsed_url.scheme == "javascript":
            continue

        # The link leads to a third-party resource - not a navigation tool on the page
        if (not page.netloc and page.netloc != parsed_url.netloc) or page.path != parsed_url.path:
            continue

        if check_grid:
            href_match = href_regex.match(link.source)
            # Link has '#' as its href
            if href_match is not None and href_match.group(1) == "#":
                continue

        links.remove(link)
        navigation_links.append(link)
        return True
    else:
        return False


def find_logo_link(driver: webdriver.Firefox, home_page: ParseResult) -> bool:
    """
    find the logo link to the home page
    :param driver:
    :param home_page:
    :return:
    """
    links = [link for link in driver.find_elements_by_xpath(
        f"//a[(@href='{home_page.path}' or contains(@href, '{home_page.netloc}{home_page.path}')) and child::img]"
    ) if is_visible(link, driver)]
    return any([link.get_attribute("outerHTML").lower().find('logo') != -1
                and urlparse(link.get_attribute("href")).path == '/' for link in links])


def check_links(driver: webdriver.Firefox, navigation_links: List[Element], links: List[Element],
                home_page: ParseResult, pages: List[ParseResult], check_grid: bool = True) -> bool:
    """
    check that all pages from the sitemap are included in the list of links and the home page is also included
    :param driver:
    :param navigation_links: list of web elements with the <a> tag
    :param links: list of web elements with the <a> tag
    :param home_page:
    :param pages:
    :param check_grid: flag to check that the link contains '#' in the href attribute
    :return:
    """
    href_regex = re.compile(r'''<a [^>]*href="([^"]*)"''')
    return all([find_page_in_links_list(driver, navigation_links, links, page, check_grid, href_regex) for page in pages]) and (
        find_page_in_links_list(driver, navigation_links, links, home_page, check_grid, href_regex) or
        find_logo_link(driver, home_page)
    )


def find_list_for_navigation(driver: webdriver.Firefox, elements: List[Element], home_page: ParseResult,
                             pages: List[ParseResult], check_description: bool = False) -> List[Element]:
    """
    The function looks for the number of lists from links that are marked as navigation
    :param driver:
    :param elements: list of web elements with the <ul>/<ol> tag
    :param home_page:
    :param pages:
    :param check_description:
    :return:
    """
    for elem in elements:
        links = elem.find_by_xpath('descendant::a', driver)
        navigation_links = []
        if links and check_links(driver, navigation_links, links, home_page, pages, False):
            if not check_description or any([elem.source.lower().find(word) != -1 for word in WORD_LIST]):
                return navigation_links
            else:
                header = get_list_header(driver, elem)
                if any([header.find(word) != -1 for word in WORD_LIST]):
                    return navigation_links
    return []


def find_site_map(driver: webdriver.Firefox, links: List[Element], home_page: ParseResult,
                  pages: List[ParseResult]) -> bool:
    """
    this method looks for a link to the Sitemap on the page and checks its correctness
    :param driver:
    :param links: list of web elements with the <a> tag
    :param home_page:
    :param pages:
    :return:
    """
    for link in links:
        url = link.get_attribute(driver, "href")
        if url is None:
            continue

        if urlparse(url).netloc == home_page.netloc and any([link.source.lower().find(w) != -1 for w in ['sitemap', 'map']]):
            current_window = driver.current_window_handle
            driver.execute_script(f"window.open('{url}')")
            driver.switch_to.window(driver.window_handles[-1])
            main = driver.find_elements_by_tag_name('main')
            ul = main[0].find_by_xpath('/ul') if main else None
            res = ul is not None and find_list_for_navigation(driver, ul, home_page, pages)
            driver.close()
            driver.switch_to.window(current_window)
            return res
    return False


def find_visible_links_by_href(driver: webdriver.Firefox, url: str) -> List[Element]:
    """
    checking that the link from the sitemap is visible on the page
    :param driver:
    :param url: the link address you are looking for
    :return:
    """
    parsed_url = urlparse(url)
    links = driver.find_elements_by_xpath(
        f"//a[@href='{parsed_url.path}' or contains(@href, '{parsed_url.netloc}{parsed_url.path}')]"
    )
    return list(filter(lambda l: is_visible(l, driver), links))


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator) -> dict:
    """
    the test checks that there are several ways to navigate the page
    :param webdriver_instance:
    :param activity:
    :param element_locator:
    :return: result = {
                'status': <'ERROR', 'PASS', 'FAIL>,
                'message': <string>,
                'elements': [{'source': Element, 'problem': <string>,
                            'screenshot': <tempfile path>, 'severity': 'WARN'/'FAIL'}],
                'checked_elements': [<body>],
             }
    """
    driver = webdriver_instance
    activity.get(driver)
    file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    driver.save_screenshot(file.name)
    body = element_locator.get_all_of_type(driver, element_types=['body'])
    result = {
        "elements": [],
        "status": "PASS",
        "message": "MultipleWays: There are several ways to navigate the site.",
        "checked_elements": body
    }

    sitemap = SiteMap(activity.url, "simple", '')
    pages = [urlparse(page['url']) for page in sitemap.get_sitemap() if find_visible_links_by_href(driver, page['url'])]
    home_page = next(filter(lambda p: not p.path, pages)) if any([not p.path for p in pages]) else urlparse(activity.url)
    try:
        pages.remove(home_page)
    except ValueError:
        pass

    functions = [check_links, find_site_map, find_list_for_navigation, find_search_input_area]
    arguments = list()
    arguments.append((driver, element_locator.get_all_of_type(driver, element_types=['a']), home_page, pages))
    arguments.append((driver, element_locator.get_all_by_xpath(driver, "//body//*[self::ul[not(ancestor::nav)] or self::ol[not(ancestor::nav)]]"), home_page, pages))
    arguments.append((driver, element_locator.get_all_by_xpath(driver, "//input[@type='text' or @type='search']")))
    counter = 0
    navigation_links = []
    while counter < 2:
        if not len(functions):
            result["status"] = "FAIL"
            result["message"] = "MultipleWays: You have fewer than two ways to navigate a group of web pages, or your" \
                                " navigation methods are incorrect."
            result['elements'] = [{
                "element": body[0],
                "problem": f"MultipleWays error: {counter} navigation method found",
                "screenshot": file.name,
                "severity": "FAIL" if len(pages) > 4 or not counter else "WARN"
            }]
            break
        func = functions.pop()
        res = func(*arguments.pop())
        if isinstance(res, list):
            navigation_links.extend(res)
            arguments = [(
                driver, navigation_links,
                list(filter(lambda x: x not in navigation_links, element_locator.get_all_of_type(driver, element_types=['a']))),
                home_page, pages)] + arguments
        counter += bool(res)
    print(result)
    return result
