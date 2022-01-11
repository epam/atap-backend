from selenium import webdriver

from framework.element import Element


def get_common_ancestor(driver: webdriver.Firefox, elem1: Element, elem2: Element, or_self=False):
    if not or_self:
        ancestors1 = elem1.safe_operation_wrapper(lambda e: e.find_by_xpath('ancestor::*', driver), on_lost=lambda: [])[::-1]
        ancestors2 = elem2.safe_operation_wrapper(lambda e: e.find_by_xpath('ancestor::*', driver), on_lost=lambda: [])[::-1]
    else:
        ancestors1 = elem1.safe_operation_wrapper(lambda e: e.find_by_xpath('ancestor-or-self::*', driver), on_lost=lambda: [])[::-1]
        ancestors2 = elem2.safe_operation_wrapper(lambda e: e.find_by_xpath('ancestor-or-self::*', driver), on_lost=lambda: [])[::-1]
    for ancestor in ancestors1:
        if ancestor in ancestors2:
            return ancestor
    return None
