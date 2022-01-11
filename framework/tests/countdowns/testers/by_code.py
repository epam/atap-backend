from time import sleep
from selenium import webdriver

from framework.element import Element
from framework.tests.countdowns.interface import Test


class TestByElements(Test):
    @staticmethod
    def changed(webdriver_instance: webdriver.Chrome, element_locator) -> []:
        """
        This method check all elements in HTML with not empty text and if element can be converted to float,
        then after 2 sec sleep, again check all element for changes.
        After if have changes returned list with updated items.

        :param element_locator:
        :param webdriver_instance: webdriver of browser
        :return: list with list pf problems elements, or empty list
        .. note::
            At this moment, this is the best solution for finding timers.
            But not absolute
        """
        def is_number(el):
            """Return can a string be converted to float"""
            try:
                float(el)
                return True
            except ValueError:
                return False
        print("====>Start testing by parse code")
        bad_elements = []
        elements = element_locator.get_all_by_xpath(webdriver_instance, "//body//*")
        before = {x: x.get_text(webdriver_instance) for x in elements if is_number(x.get_text(webdriver_instance))}
        if not before:
            return []
        sleep(5)
        changed = [x for x in elements if x in before and x.get_text(webdriver_instance) != before[x]]
        for element in changed:
            bad_elements.append({
                "element": Element(element, webdriver_instance),
                "problem": "Element has changed"
            })
        return bad_elements
