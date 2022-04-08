""" Test in used in dependencies to get "button", "div", "a", "span", "img", "select", "input" elements
    which are not links.

"""
import re

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

from framework.libs.test_pattern import SuperTest
from framework.element_locator import ElementLocator
from framework.element import Element, ElementLostException



__all__ = []

framework_version = 2
locator_required_elements = ["button", "div", "a", "span", "img", "select", "input"]
depends = []
webdriver_restart_required = True
elements_type = "button"
test_data = [
    {
        "page_info": {
            "url": r"page_good_buttons.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"page_noelements.html"},
        "expected_status": "NOELEMENTS"
    },
]
POSSIBLE_KEYWORDS = r"button|btn|checkbox|check"


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return ButtonsPurpose(webdriver_instance, activity, element_locator, dependencies).get_result()


class ButtonsPurpose(SuperTest):
    __slots__ = "buttons", "result"

    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.buttons = {
            "links": [],
            "buttons": [],
            "possible_buttons": [],
        }
        self._main()

    def _main(self):
        if self._collect_buttons():
            self._filter(self.buttons["links"] + self.buttons["possible_buttons"])
            if any(self.buttons.values()):
                self.set_pass_status()
            self._push_dependency()

    def _collect_buttons(self):
        """ Collect all active elements that might be buttons using element locator.
            Set result status from "NOELEMENTS" to "PASS".
            Call purpose check
        """
        locator_elements = self.locator.get_activatable_elements()
        if locator_elements:
            print("\nClicking elements")
            Element.safe_foreach(locator_elements, self._click_sort)
            return True
        return False

    def _click_sort(self, element):
        """ Sort active elements for possible buttons and links.
            :param element: Framework element
        """
        if element.tag_name == 'a' and 'href="#' not in element.source and 'href=""' not in element.source and \
                'href="?' not in element.source:
            self.buttons["links"].append(element)
            return
        elif element.tag_name == "input" and self.get_attribute(element, "type") not in ("button", "submit", "reset"):
            return
        elif element.tag_name == "img" and self.get_attribute(element, "role") != "button":
            return

        self._page_refresh()
        self.scroll_to_el(element)
        # if element.tag_name == "span":
        #     print("Click span")
        #     print(element.source[:240:])
        action = element.click(self.driver)["action"]
        # if element.tag_name == "span":
        #     print("Action")
        #     print(action, '\n')
        if action == "NONE":
            self.buttons["possible_buttons"].append(element)

        elif action in ("NEWTAB", "PAGECHANGE"):
            self.buttons["links"].append(element)

    @staticmethod
    def fix_outer_html(outer: str) -> str:
        """By undefined reason after click there are changes in element outerHTML.
        This method remove empty style attribute.

        """
        return outer.replace(' style=""', "", 1)

    def _push_dependency(self):
        # print()
        # print("RESULT")
        # for elem in self.buttons["buttons"]:
        #     print(repr(elem.source[:240:]))
        self.result["dependency"] = self.buttons["buttons"]

    def _filter(self, clickable_elements: list):
        """ Filter elements to avoid fake clicks
        :param clickable_elements: list of active UI elements
        :return:

        """
        # print("FILTERS\n")
        # print("BEFORE FILTERS")
        # for element in clickable_elements:
        #     print(repr(element.source[:240]))
        first_filter = self._nesting_filter(clickable_elements)
        # print("\nAfter nesting filter")
        # for element in first_filter:
        #     print(repr(element.source[:240]))
        second_filter = self._position_filter(first_filter)
        # print("\nAfter position filter")
        # for element in second_filter:
        #     print(repr(element.source[:240]))
        third_filter = self._text_filter(second_filter)
        # print("\nAfter text filter")
        # for element in third_filter:
        #     print(repr(element.source[:240]))
        filter_result = self._additional_div_filter(third_filter)
        # print("\nAfter additional div filter")
        # for element in filter_result:
        #     print(repr(element.source[:240]))
        for element in filter_result:
            if element not in self.buttons["links"]:
                # if element.tag_name in ['div', 'a']:
                #     self.buttons["role_test_data"].append(element)
                self.buttons["buttons"].append(element)
        self.buttons.pop("possible_buttons")

    def _position_filter(self, elements: list):
        """Filter elements which have the same position on the page (X, Y)
        :param elements: list of active UI elements
        :return list: smallest elements at positions or elements which cannot have child elements

        """
        elements_coords = set()
        not_lost_elements = list()
        filtered_elements = list()
        for element in elements:
            try:
                selenium_element = element.get_element(self.driver)
            except (StaleElementReferenceException, ElementLostException, NoSuchElementException):
                continue
            elements_coords.add(f"{selenium_element.rect['x']}:{selenium_element.rect['y']}")
            not_lost_elements.append(element)
        elements_at_coords = {coord: [] for coord in elements_coords}
        for element in not_lost_elements:
            try:
                selenium_element = element.get_element(self.driver)
                elements_at_coords[f"{selenium_element.rect['x']}:{selenium_element.rect['y']}"].append(element)
            except (StaleElementReferenceException, ElementLostException, NoSuchElementException):
                continue
            except KeyError:
                continue

        for coord, elements_ in elements_at_coords.items():
            if not elements_:
                continue
            if len(elements_) == 1:
                filtered_elements.append(elements_[0])
                continue
            else:
                smallest_container = elements_[0]
                detected = False
                for element in elements_:
                    if element.tag_name in ("button", "a", "input"):
                        filtered_elements.append(element)
                        detected = True
                        break
                    else:
                        try:
                            selenium_element = element.get_element(self.driver)
                            selenium_smallest_container = smallest_container.get_element(self.driver)
                        except (StaleElementReferenceException, ElementLostException, NoSuchElementException):
                            continue
                        if selenium_element.rect["height"] < selenium_smallest_container.rect["height"] or (
                                selenium_element.rect["width"] < selenium_smallest_container.rect["width"]):
                            smallest_container = element
                if not detected:
                    filtered_elements.append(smallest_container)

        return filtered_elements

    def _nesting_filter(self, elements: list):
        """ Remove parent elements (like <div>, <span>, etc.) of the clickable element.
        :param elements: list of framework elements
        :return: list of framework elements

        """
        filtered_elements = list()
        for index, element in enumerate(elements):
            try:
                descendants = element.find_by_xpath("descendant::*", self.driver)
            except (StaleElementReferenceException, ElementLostException, NoSuchElementException):
                continue
            if not descendants:
                filtered_elements.append(element)
                continue
            initial_elements = elements[:]
            initial_elements.pop(index)
            have_descendants = False
            for other_element in initial_elements:
                if other_element in descendants:
                    have_descendants = True
                    break
            if not have_descendants:
                filtered_elements.append(element)
        return filtered_elements

    def _text_filter(self, elements: list):
        """ Remove <div> elements which are text

        :param elements: list of active UI elements
        :return: list of framework elements
        """
        filtered_elements = list()
        for element in elements:
            if element.tag_name in ("div", "span"):
                html = element.source
                # if re.search(r"<code>|<br>|<span>|<h2>|<p>", html):
                if re.search(r"<code|<br|<h2|<p", html) or len(element.get_text(self.driver)) < 10:
                    continue
            #   Was disabled because of "WARN" status
            #     elif not re.search(POSSIBLE_KEYWORDS, html):
            #         """Strong restriction. Reason - locator detects interactable (clickable)
            #         text and there is no way to filter it.
            #
            #         """
            #         continue
            elif element.tag_name == "img":
                if element.get_parent(self.driver).tag_name == "a":
                    continue
            filtered_elements.append(element)
        return filtered_elements

    def _additional_div_filter(self, elements: list):
        filter_result = []
        for element in elements:
            if element.tag_name != "div":
                filter_result.append(element)
                continue
            element_innerHTML = self.get_attribute(element, "innerHTML")
            if not any(list(map(lambda x: x in element_innerHTML, ("button", "input")))):
                filter_result.append(element)
        return filter_result
