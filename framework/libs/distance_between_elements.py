from selenium import webdriver
import math

from framework.element import Element


class Point:
    def __init__(self, x_init, y_init):
        self.x = x_init
        self.y = y_init

    def distance(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __str__(self):
        return f'Point({self.x}, {self.y})'


class Rectangle:
    def __init__(self, driver: webdriver.Firefox, element):
        element = element.get_element(driver) if isinstance(element, Element) else element
        self.x, self.y = element.location.values()
        self.h, self.w = element.size.values()
        self.top_left_point = Point(self.x, self.y)
        self.bottom_right_point = Point(self.x + self.w, self.y + self.h)

    def distance(self, other):
        left = other.bottom_right_point.x < self.top_left_point.x
        right = self.bottom_right_point.x < other.top_left_point.x
        bottom = other.bottom_right_point.y < self.top_left_point.y
        top = self.bottom_right_point.y < other.top_left_point.y
        if top and left:
            return Point(self.top_left_point.x, self.bottom_right_point.y).distance(Point(other.bottom_right_point.x,
                                                                                          other.top_left_point.y))
        elif left and bottom:
            return self.top_left_point.distance(other.bottom_right_point)
        elif bottom and right:
            return Point(self.bottom_right_point.x, self.top_left_point.y).distance(Point(other.top_left_point.x,
                                                                                          other.bottom_right_point.y))
        elif right and top:
            return self.bottom_right_point.distance(other.top_left_point)
        elif left:
            return self.top_left_point.x - other.bottom_right_point.x
        elif right:
            return other.top_left_point.x - self.bottom_right_point.x
        elif bottom:
            return self.top_left_point.y - other.bottom_right_point.y
        elif top:
            return other.top_left_point.y - self.bottom_right_point.y
        else:  # rectangles intersect
            return 0.

    def contains(self, other):
        return (self.top_left_point.x <= other.top_left_point.x and self.top_left_point.y <= other.top_left_point.y and
                self.bottom_right_point.x >= other.bottom_right_point.x
                and self.bottom_right_point.y >= other.bottom_right_point.y)

    def __str__(self):
        return f'Rectangle with points: {self.top_left_point},\n{self.bottom_right_point}\n'


def distance(driver: webdriver.Firefox, elem1, elem2) -> float:
    return Rectangle(driver, elem1).distance(Rectangle(driver, elem2))


def contains(driver: webdriver.Firefox, elem1, elem2) -> bool:
    return Rectangle(driver, elem1).contains(Rectangle(driver, elem2))


def intersection(driver: webdriver.Firefox, elem1, elem2) -> bool:
    rectangle1 = Rectangle(driver, elem1)
    rectangle2 = Rectangle(driver, elem2)
    top1, bottom1, left1, right1 = rectangle1.y, rectangle1.y + rectangle1.h, rectangle1.x, rectangle1.x + rectangle1.w
    top2, bottom2, left2, right2 = rectangle2.y, rectangle2.y + rectangle2.h, rectangle2.x, rectangle2.x + rectangle2.w
    return top2 <= bottom1 and top1 <= bottom2 and left2 <= right1 and left1 <= right2
