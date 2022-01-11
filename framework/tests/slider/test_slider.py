import copy
from itertools import combinations
from typing import List

from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException, JavascriptException, WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator

name = "Ensures that some elements such as sliders, works well, when used keyboard"
webdriver_restart_required = False
framework_version = 0
WCAG = "2.1.1"
KEYS = {
    Keys.ARROW_RIGHT,
    Keys.ARROW_UP,
    Keys.ARROW_LEFT,
    Keys.ARROW_DOWN,
    Keys.HOME,
    Keys.END,
    Keys.PAGE_UP,
    Keys.PAGE_DOWN
}

elements_type = "slider"
test_data = [
    {
        "page_info": {
            "url": "sliders/page_good_sliders.html"
        },
        "expected_status": "PASS",
    },

    {
        "page_info": {
            "url": "sliders/page_bugs_slider_1.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1

    },

    {
        "page_info": {
            "url": "sliders/page_bugs_slider_2.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    },

    # {
    #     "page_info": {
    #         "url": "sliders/page_bugs_slider_3.html"
    #     },
    #     "expected_status": "FAIL",
    #     "expected_problem_count": 1
    # },

    {
        "page_info": {
            "url": "sliders/page_good_slider_4.html"
        },
        "expected_status": "PASS",
    },

    {
        "page_info": {
            "url": "sliders/page_bugs_sliders.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 4
    }
]


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    return Slider(webdriver_instance, element_locator, activity).result()


class Slider:
    def __init__(self, driver: webdriver.Firefox, locator: ElementLocator, activity):
        self._dr = driver
        self._loc = locator
        self._ac = activity

    def refresh(self):
        return self._ac.get(self._dr)

    def result(self):
        result = {
            "status": "PASS",
            "message": "",
            "elements": [],
            "checked_elements": [],
        }
        elements, checked = self.main()
        if elements is None:
            result["status"] = "NOELEMENTS"
            result["message"] = "No elements like sliders"
        elif elements:
            result["status"] = "FAIL"
            result["elements"] = elements
            result["message"] = "Bad sliders"
        else:
            result["message"] = "All sliders working"
        result["checked_elements"] = checked
        return result

    def main(self):
        xpath = "//body//*[self::div[@role='slider'] or self::input[@type='range']]"
        sliders = self._loc.get_all_by_xpath(self._dr, xpath)
        sliders.extend(self.possible_sliders())
        if not sliders:
            return None, []
        self.refresh()
        return self.bad_working_sliders(sliders), sliders

    def bad_working_sliders(self, elements: List[Element]):
        bad_elements = []
        for count, slider in enumerate(elements):
            print(f"====>Check {count} element of {len(elements)} elements")
            self.refresh()
            if self._check_interactable(slider) is None:
                continue
            self.refresh()
            messages = slider.safe_operation_wrapper(self._keys, self.lost_element_exc)
            if messages:
                bad_elements.extend(messages)
        return bad_elements

    def _check_interactable(self, el):
        try:
            el.get_element(self._dr).send_keys("")
        except ElementNotInteractableException:
            return None
        return el

    def _keys(self, el: Element):
        before = self.all_attrs(el)
        for key in KEYS:
            self.refresh()
            try:
                elem = el.get_element(self._dr)
                ActionChains(self._dr).send_keys_to_element(elem, key).perform()
            except JavascriptException:
                return []
            after = self.all_attrs(el)
            if not set(before).difference(set(after)):
                return [{
                    'element': el,
                    'problem': "Not worked buttons"
                }]
        return []

    def lost_element_exc(self):
        """Element lost"""
        pass

    def contains_element_attrs(self, element: Element, word):
        """
        Search attributes of the element keyword
        """
        return any(el for el in list(element.get_attributes(self._dr).values()) if word in el)

    def possible_sliders(self) -> List[Element]:
        """
        :return:
        """
        sliders = []
        elems = {
            "self::div",
            "self::input",
            "self::svg"
        }
        elements = self._loc.get_all_by_xpath(self._dr, f"//body//*[{' or '.join(elems)}]")

        def safe_intersects(sliders_: List[Element]) -> List[Element]:  # SO LONG TIME
            print("====>Something is works")
            unique = copy.deepcopy(sliders_)
            for el1, el2 in combinations(unique, 2):
                try:
                    if el2 in el1.find_by_xpath('./ancestor::*', self._dr) or\
                            not el1.safe_operation_wrapper(safe_send, self.lost_element_exc):
                        unique.remove(el1)
                    elif el1 in el2.find_by_xpath('./ancestor::*', self._dr) or\
                            not el2.safe_operation_wrapper(safe_send, self.lost_element_exc):
                        unique.remove(el2)
                except ValueError:
                    continue
            return list(unique)

        def safe_send(element):
            try:
                element.get_element(self._dr).send_keys("")
                return True
            except ElementNotInteractableException:
                return False

        for el in elements:
            if any(el for el in list(el.get_attributes(self._dr).values()) if "slider" in el):
                sliders.append(el)
        return safe_intersects(sliders)

    def all_attrs(self, el: Element):
        """Method to get all attributes from an element"""
        attrs = list(el.get_attributes(self._dr, True).values())
        elements = el.find_by_xpath(".//*", self._dr)
        for e in elements:
            attrs.extend(list(e.get_attributes(self._dr, True).values()))
        return attrs



