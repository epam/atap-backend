import itertools
import re
import time
from typing import List, Optional, Set, Dict

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

from framework.activity import Activity
from framework.element import Element, ElementLostException

POTENTIAL_ACTIVATORS = {"a", "button", "input", "div"}
DEFAULT_TARGET_ELEMENTS = {"a", "button", "input", "img", "div", "select"}


class _ElementInfo:
    def __init__(self, element: Element, is_displayed):
        self.element = element
        self.displayed_from_start = is_displayed
        self.displayed_ever = is_displayed
        self.activating_element: Optional[Element] = None

    def set_activated_by(self, element: Element):
        if self.displayed_from_start:
            return
        self.activating_element = element
        self.displayed_ever = True


class ElementNeverActivatesException(Exception):
    pass


class ElementLocator:
    def __init__(self, webdriver_instance: webdriver.Firefox, activity: Activity, target_elements: Set[str]):
        self.webdriver_instance = webdriver_instance
        self.activity = activity
        self.final_url = activity.url
        self.target_elements = target_elements
        self.known_elements: Dict[str, List[_ElementInfo]] = {}
        url_pattern = r"""https?://"""
        self.url_regex = re.compile(url_pattern)
        self.href_regex = re.compile(r'''<a [^>]*href="([^#j][^"]*)"''')

    def _initial_scan(self, counter=0, progress_report_callback=None) -> None:
        print("Looking for elements:")
        for element_type in self.target_elements:
            if element_type not in self.known_elements:
                self.known_elements[element_type] = []
            new_elements = self.webdriver_instance.find_elements_by_tag_name(element_type)
            if progress_report_callback is not None:
                progress_report_callback(
                    {"thread_status": {0: f"Element locator adding {len(new_elements)} <{element_type}> elements"}}
                )

            for element in new_elements:
                counter += 1
                print(f"\rAdding <{element_type}> {counter}/{len(new_elements)}", end="", flush=True)
                try:
                    self.known_elements[element_type].append(
                        _ElementInfo(Element(element, self.webdriver_instance), element.is_displayed())
                    )
                except StaleElementReferenceException:
                    print()
                    print("Element was lost before being added, skipping")
            counter = 0
            print("")
        print(f"Found {len(self.known_elements)} elements")

    def _update_state_diff(self, activating_element: Element) -> None:
        # Will ignore any new elements
        elements_appeared = 0
        for element_info in itertools.chain.from_iterable(self.known_elements.values()):
            try:
                is_displayed_now = element_info.element.get_element(self.webdriver_instance).is_displayed()
                if is_displayed_now and not element_info.displayed_from_start:
                    element_info.set_activated_by(activating_element)
                    elements_appeared += 1
            except ElementLostException:
                print()
                print(f"Element lost! {element_info.element.source}")
        if elements_appeared:
            print(f" --- {elements_appeared} elements appeared")

    def analyze(self, fake=True, progress_report_callback=None) -> None:
        print("Running activator check")
        self.activity.get(self.webdriver_instance)
        time.sleep(5)
        self.final_url = self.webdriver_instance.current_url
        activators = list()
        for element_type in POTENTIAL_ACTIVATORS:
            new_elements = self.webdriver_instance.find_elements_by_tag_name(element_type)
            for element in new_elements:
                # if element.tag_name == "a":
                #     href_match = self.href_regex.match(element.get_attribute("outerHTML"))
                #     if href_match:
                #         continue
                try:
                    activators.append(Element(element, self.webdriver_instance))
                except StaleElementReferenceException:
                    print()
                    print("Element was lost before being added, skipping")

        self._initial_scan(progress_report_callback=progress_report_callback)

        if not fake and len(self.target_elements) != 0:
            for activator_id, activator in enumerate(activators, 1):
                # element_source = activator.get_element(self.webdriver_instance).get_attribute('outerHTML')
                print(f"\rTesting activator {activator_id}/{len(activators)}", end="", flush=True)
                click_result = activator.click(self.webdriver_instance)
                if click_result["action"] == "NEWTAB":
                    print(" --- A new tab was opened")
                elif click_result["action"] == "PAGECHANGE":
                    print(" --- Page changed")
                elif click_result["action"] == "ALERT":
                    print(" --- Alert popped up")
                elif click_result["action"] == "NONE":
                    self._update_state_diff(activator)
                self.webdriver_instance.get(self.final_url)
                time.sleep(0.5)
            print()
        # Remove elements that always stay hidden
        for element_info_list in self.known_elements.values():
            element_info_list[:] = itertools.filterfalse(
                lambda element_info: not element_info.displayed_ever, element_info_list
            )

    @staticmethod
    def get_all_of_type(webdriver_instance: webdriver.Firefox, element_types=None) -> List[Element]:
        elements = []
        for element_type in element_types:
            elements.extend(
                Element.from_webelement_list(
                    webdriver_instance.find_elements_by_tag_name(element_type), webdriver_instance
                )
            )
        return elements

    @staticmethod
    def get_all_by_xpath(webdriver_instance, xpath) -> List[Element]:
        return Element.from_webelement_list(webdriver_instance.find_elements_by_xpath(xpath), webdriver_instance)

    def get_activatable_elements(self, element_types=None) -> List[Element]:
        if element_types is None:
            element_types = DEFAULT_TARGET_ELEMENTS

        filtered_elements = []
        for (k, v) in self.known_elements.items():
            if k in element_types:
                filtered_elements.append(v)
        return list(
            map(lambda element_info: element_info.element, itertools.chain.from_iterable(filtered_elements))
        )

    def activate_element(self, element: Element):
        for known_element in itertools.chain.from_iterable(self.known_elements.values()):
            if known_element.element == element:
                if not known_element.displayed_ever:
                    raise ElementNeverActivatesException()
                print(f"Getting final_url:{self.final_url}")
                self.webdriver_instance.get(self.final_url)
                time.sleep(0.5)
                if known_element.displayed_from_start:
                    # Already activated
                    return
                else:
                    known_element.activating_element.get_element(self.webdriver_instance).click()
                    time.sleep(0.5)
                    # Should be active now

    def is_displayed_from_start(self, element: Element):
        for known_element in itertools.chain.from_iterable(self.known_elements.values()):
            if known_element.element == element:
                return known_element.displayed_from_start
        else:
            return None

    def click(self, element: Element, webdriver_instance: webdriver.Firefox):
        # self.activate_element(element)
        return element.click(webdriver_instance)
