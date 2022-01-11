import time
from selenium import webdriver
from typing import List
import re


from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.list.lib import is_visible, get_children, WebList


locator_required_elements = ["div", 'ul', 'ol', 'p']
webdriver_restart_required = False
IGNORED_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
framework_version = 0


def clean_html(raw_html):
    """Clear html code from html elements"""

    return re.sub('[@#$&{}()">]', ' ', re.sub(re.compile('<[\w\W]*?>'), '', raw_html)).strip()


def text_is_present(element: Element, driver: webdriver.Firefox):
    return element.safe_operation_wrapper(lambda l: l.get_text(driver), on_lost=lambda: '') \
        if is_visible(driver, element) else clean_html(element.source)


def list_candidate_locator(driver: webdriver.Firefox, element_locator: ElementLocator):
    candidates = element_locator.get_all_by_xpath(
        driver,
        "//*[(self::div or self::p or self::main) and not(ancestor::table) and not(ancestor::ul) and not(ancestor::ol)]"
    )
    lists = []
    lonely_lists = []
    horizontal_lists = []

    def check(elem: Element):
        if not is_visible(driver, elem):
            return None
        if elem.tag_name == 'p':
            lonely_lists.append(WebList(elem, [], axis='x', lonely=True))
            return None
        children = get_children(driver, elem)
        if len(children) < 2:
            lonely_lists.append(WebList(elem, [], axis='x', lonely=True))
            return None

        for axis in ['x', 'y']:
            if (children[0].tag_name == children[1].tag_name
                    and children[0].get_element(driver).location[axis] == children[1].get_element(driver).location[axis]):
                header = None
                tag = children[0].tag_name
                location = children[0].get_element(driver).location[axis]
                elements = children[:2]
            else:
                header = children[0]
                tag = children[1].tag_name
                location = children[1].get_element(driver).location[axis]
                elements = [children[1]]

            for child in children[2:]:
                if not is_visible(driver, child) or child.tag_name != tag or child.get_element(driver).location[axis] != location:
                    break
                else:
                    elements.append(child)
            if len(elements) >= 2 and any([elem.tag_name not in IGNORED_TAGS for elem in elements]):
                if axis == 'y':
                    horizontal_lists.append(WebList(elem, elements, axis='y', header=header, lonely=False))
                else:
                    lists.append(WebList(elem, elements, axis='x', header=header, lonely=False))
                return None
            elif elem.get_text(driver) and axis == 'x':
                lonely_lists.append(WebList(elem, [], axis=axis, header=header, lonely=True))
    Element.safe_foreach(candidates, check)
    return lists, lonely_lists, horizontal_lists


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    start = time.time()
    candidate_lists, lonely_lists, horizontal_lists = list_candidate_locator(webdriver_instance, element_locator)
    print(f"time to locate candidates = {time.time() - start}")

    return {
        'status': "PASS",
        'message': '',
        'elements': [],
        'checked_elements': [],
        'native_lists': element_locator.get_all_of_type(webdriver_instance, element_types=['ul', 'ol']),
        'candidate_lists': candidate_lists,
        'horizontal_lists': horizontal_lists,
        'lonely_lists': lonely_lists
    }
