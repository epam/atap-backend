from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webelement import WebElement

from framework.element import Element
from framework.libs.element_rect import WebElementRect

EPSILON = 1


class ElementWrapper:

    def __init__(self, element, driver: webdriver.Firefox):
        self._web_el = element if isinstance(element, WebElement) else None
        self._el = element if isinstance(element, Element) else Element(element, driver)
        self._dr = driver
        self._ac = ActionChains(self._dr)
        self._web_rect = WebElementRect

    def _refresh(self):
        self._ac = ActionChains(self._dr)

    def __getitem__(self, item):
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_el.get_attribute(item)

    @property
    def action(self):
        """
        :return: instance of ActionChains
        """
        self._refresh()
        return self._ac

    @property
    def text(self):
        """
        :return: instance of WebElement
        """
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_el.text

    @property
    def element(self):
        """
        :return: instance of WebElement
        """
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_el

    @property
    def framework_element(self):
        """
        :return: instance of Element
        """
        return self._el

    @property
    def location(self):
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_el.location.values()

    @property
    def size(self):
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_el.size.values()

    @property
    def coords(self):
        x, y = self.location
        h, w = self.size
        return [x, y, x + w, y + h]

    @property
    def is_visible(self):
        h, w = self.size
        x, y = self.location
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return h > EPSILON and w > EPSILON and x >= 0 and y >= 0 and self._web_el.is_displayed()

    @property
    def rect_elem(self):
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_rect(self._web_el)

    def send_key(self, key):
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        self._web_el.send_keys(key)

    def min_distance(self, second_element):
        return self.rect_elem.get_min_distance(second_element.rect_elem)

    def css_property(self, prop):
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_el.value_of_css_property(prop)

    def send_keys(self, value):
        if self._web_el is None:
            self._web_el = self._el.get_element(self._dr)
        return self._web_el.send_keys(value)
