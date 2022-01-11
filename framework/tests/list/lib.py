from selenium import webdriver
from dataclasses import dataclass
from typing import List

from framework.element import Element


@dataclass
class WebList(object):
    """the class that stores the intended list: the parent web item, the title(if any), and the list items themselves"""

    def __init__(self, parent: Element, elements: List[Element], axis: str, header: Element = None, method: str = None,
                 lonely=None):
        self.parent: Element = parent
        self.axis = axis
        self.header = header
        self.elements = elements
        self.method = method
        self.lonely = lonely

    def __eq__(self, other):
        return self.parent.source == other.parent.source

    def __hash__(self):
        return hash(self.parent.source)

    def __repr__(self) -> str:
        return f'WebList({self.parent})'


def get_children(driver: webdriver.Firefox, elem: Element) -> List[Element]:
    return elem.safe_operation_wrapper(lambda e: e.find_by_xpath("child::*", driver), lambda: [])


def is_visible(driver: webdriver.Firefox, elem: Element):
    element = elem.get_element(driver)
    return element and element.size['width'] * element.size['height'] > 0 and element.is_displayed()


def check_correct_role_for_list_items(driver: webdriver.Firefox, list_: WebList) -> bool:
    return all([item.get_attribute(driver, "role") == 'listitem' for item in list_.elements])


def check_correct_role_for_list(driver: webdriver.Firefox, suspect_list: WebList) -> bool:
    current_elem = suspect_list.parent
    while current_elem.get_attribute(driver, "role") != 'list' and len(get_children(driver, current_elem)) == 1:
        new_elem = current_elem.get_parent(driver)
        if new_elem is None:
            break
        else:
            current_elem = new_elem
    return current_elem.get_attribute(driver, "role") == 'list'
