from itertools import product

import numpy as np
from selenium.webdriver.remote.webelement import WebElement


class WebElementRect:
    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def distance(self, p) -> float:
            return np.sqrt((self.x - p.x) ** 2 + (self.y - p.y) ** 2)

    def __init__(self, el: WebElement = None):
        if not isinstance(el, WebElement) and el is not None:
            raise TypeError("Incorrect type object")
        if el is not None and isinstance(el, WebElement):
            self.x, self.y = el.location.values()
            self.height, self.width = el.size.values()
            self.x1 = self.x + self.width
            self.y1 = self.y + self.height
            self._el = el
            self._is_visible = el.size['width'] * el.size['height'] > 0

    def __eq__(self, other):
        if not isinstance(other, WebElementRect):
            return NotImplemented
        return self.coords() == other.coords()

    def element(self):
        return self._el

    def coords(self):
        return [self.x, self.y, self.x1, self.y1]

    @classmethod
    def from_rect(cls, x: float, y: float, w: float, h: float):
        obj = cls()
        obj.x = x
        obj.y = y
        obj.x1 = x + w
        obj.y1 = y + h
        obj.height = h
        obj.width = w
        obj._is_visible = w * h > 0
        return obj

    def intersects(self, rect) -> bool:
        """
        This method need to know
        :param rect: ElementRect
        :return: is there an intersection with given rectangles
        """
        if not self._is_visible:
            return False
        return (rect.x <= self.x <= rect.x1 and rect.y <= self.y <= rect.y1 or
                rect.x <= self.x1 <= rect.x1 and rect.y <= self.y <= rect.y1 or
                rect.x <= self.x <= rect.x1 and rect.y <= self.y1 <= rect.y1 or
                rect.x <= self.x1 <= rect.x1 and rect.y <= self.y1 <= rect.y1)

    def plural_intersects(self, elements: dict):
        elems = []
        for el, coord in elements.items():
            if self.intersects(WebElementRect.from_rect(*coord)):
                elems.append(el)
        return elems

    def sides_centers(self):
        """
        :return:
        """
        x = (self.x1 + self.x) / 2
        y = (self.y1 + self.y) / 2
        return self.Point(x, self.y), self.Point(x, self.y1), self.Point(self.x, y), self.Point(self.x1, y)

    def get_distance(self, rect):
        return [p1.distance(p2) for p1, p2 in product(self.sides_centers(), rect.sides_centers())]

    def get_min_distance(self, rect) -> float:
        return min(self.get_distance(rect))