from typing import List, Optional

from selenium import webdriver

from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.test_pattern import DetectingTest

__all__ = []

framework_version = 2
depends = []
locator_required_elements = ["button", "a", "input", "select"]
webdriver_restart_required = True
test_data = [
    {
        "page_info": {"url": r"dropdowns/page_good_disclosure.html"},
        "expected_status": "PASS"
    },
]


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return DropdownDetector(webdriver_instance, activity, element_locator, dependencies).get_result()


class DropdownDetector(DetectingTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.dropdowns = dict()
        self._main()

    def _main(self):
        elements = self.locator.get_activatable_elements()
        for element in elements:
            if element.tag_name == "input" and self.get_attribute(element, "type") != "button":
                continue
            elif element.tag_name == "select":
                self.dropdowns.update({
                    element: {
                        "type": "selector",
                        "kbd_activation": True,
                        "hover_activation": False,
                        "click_activation": True,
                        "dd_elements": element.find_by_xpath("ancestor::*", self.driver)
                    }
                })
                continue
            detected_hover = self._detect_by_hover(element)
            detected_kbd = self._detect_by_keyboard(element)
            detected_click = self._detect_by_click(element)
            detected = detected_click or detected_kbd or detected_hover
            if detected:
                ul_cnt = 0
                for elem in detected:
                    if elem.tag_name == "ul":
                        ul_cnt += 1
                if ul_cnt > 1:
                    e_type = "disclosure"
                else:
                    e_type = "undefined"
                self.dropdowns.update({
                    element: {
                        "type": e_type,
                        "kbd_activation": bool(detected_kbd),
                        "hover_activation": bool(detected_hover),
                        "click_activation": bool(detected_click),
                        "dd_elements": detected,
                    }
                })
        for element in self.dropdowns.keys():
            data = self.dropdowns[element]
            if data["type"] != 'undefined':
                continue
            if element.tag_name == "select":
                data['type'] = 'selector'
                continue

            breakpoint_ = 0  # in case of large options amount
            for dd_element in data["dd_elements"]:
                if breakpoint_ == 10:
                    break
                self._page_refresh()
                if data["kbd_activation"]:
                    self._enter_activation(element=element)
                elif data["hover_activation"]:
                    self._pointer_activation(element=element)
                elif data["click_activation"]:
                    self._click_activation(element=element)
                if dd_element.tag_name in ('a', 'option', 'li', "div"):
                    action = dd_element.click(self.driver)["action"]
                    breakpoint_ += 1
                    if action == "NONE":
                        data["type"] = "selector"
                        continue
                    elif action in ("NEWTAB", "PAGECHANGE"):
                        data["type"] = "menu"
                        break

        for dd in self.dropdowns.keys():
            if self.dropdowns[dd]["type"] == "selector":
                if dd.tag_name == "select":
                    continue
                ul = self._get_ul(self.dropdowns[dd]['dd_elements'])
                role = self.get_attribute(ul, "role")
                if role == "menu":
                    self.dropdowns[dd]["type"] = "action"
                elif role == "listbox":
                    self.dropdowns[dd]["type"] = "listbox"
                else:
                    self.dropdowns[dd]["type"] = "selector_no_role"
        self.result["dependency"] = self.dropdowns

    def _detect_by_hover(self, element: Element) -> List[Element]:
        self._page_refresh()
        self._pointer_activation(element=element)
        size_changed_elements = self._get_zero_size_changed_elements()
        return size_changed_elements

    def _detect_by_click(self, element: Element) -> List[Element]:
        self._page_refresh()
        self._click_activation(element=element)
        size_changed_elements = self._get_zero_size_changed_elements()
        return size_changed_elements

    def _detect_by_keyboard(self, element: Element) -> List[Element]:
        self._page_refresh()
        self._enter_activation(element=element)
        size_changed_elements = self._get_zero_size_changed_elements()
        return size_changed_elements

    @staticmethod
    def _get_ul(elements: List[Element]) -> Optional[Element]:
        for element in elements:
            if element.tag_name == "ul":
                return element
