from typing import Union

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from framework.element import Element, ElementLostException


def is_visible(elem: Union[Element, WebElement], driver: webdriver.Firefox) -> bool:
    """
    Checking that the element is visible (namely, it has a non-zero width and height, and it is not disabled or enabled)
    """

    def check_visible(element: Union[Element, WebElement]) -> bool:
        if isinstance(element, Element):
            try:
                element = element.get_element(driver)
            except (ElementLostException, WebDriverException):
                return False
        return (element and element.size['width'] > 1 and element.size['height'] > 1 and element.is_displayed()
                and element.is_enabled())

    return elem.safe_operation_wrapper(check_visible, on_lost=lambda: False) if isinstance(elem, Element) else \
        check_visible(elem)
