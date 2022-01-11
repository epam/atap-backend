from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.common.exceptions import (
    InvalidArgumentException,
)
from selenium.webdriver.support.expected_conditions import (
    visibility_of,
    frame_to_be_available_and_switch_to_it,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from framework.libs.test_pattern import SuperTest
from framework.element_locator import ElementLocator
from framework.element import Element, ElementLostException
from .checkbox_scripts import locator_visible_script

import re


framework_version = 2  # Detecting test
depends = []
locator_required_elements = []
webdriver_restart_required = True
elements_type = "button|checkbox"
test_data = [
    {
        "page_info": {"url": r"checkbox/page_good_checkbox.html"},
        "expected_status": "PASS",
    },
    {"page_info": {"url": r"page_noelements.html"}, "expected_status": "NOELEMENTS"},
]
POSSIBLE_KEYWORDS = {
    "checkbox": r"checkbox|check",
    "radio": r"radio|radiobutton",
    "range": r"range|slider",
    "every": r"checkbox|check|radio|radiobutton|range|slider",
}


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    """
    Detecting test for checkbox test group.
    Based on test_buttons_purpose test.
    Locates clickable elements from locator_required_elements.
    Then filter clickables, then checks them on behavior,
    so only elements acting like checkboxes remain.
    """
    return Test(webdriver_instance, activity, element_locator, dependencies).get_result()


def _drop_bad_attrs(expression: str):
    """
    To ignore HTML code attribute changes like style=""
    """
    return re.sub(r'\s+\w+=""', "", expression)


def _fix_numeral_selector(selector: str):
    """
    Writes forbidden id selector with numeral id as r"...#\\3\d \d+..."
    """
    return re.sub(r"#\d", lambda num_id: f"#\\\\3{num_id.group()[1]} ", selector)


def get_element_opening_tag(element: WebElement):
    """
    Returns HTML code of the element's opening tag (<div ...>)
    """
    outer_html = element.get_attribute("outerHTML")
    for num, symbol in enumerate(outer_html):
        if symbol == ">":
            return outer_html[: num + 1]


# disabled
def _main_with_iframe(func):
    """
    Decorator, wrapper does the job of _main,
    but accounts all present <iframe> on the webpage
    """

    def _wrapper(test_obj):
        document = test_obj._get_iframe()
        for iframe in document:
            test_obj.activity.get(test_obj.driver)
            switched = test_obj._switch_to_iframe(iframe)
            if not switched:
                continue
            func(test_obj)
        # foreground of DOM
        test_obj.activity.get(test_obj.driver)
        func(test_obj)

    return _wrapper


class Test(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.buttons = {
            "possible_buttons": [],
            "buttons": [],
            "links": [],
            "non_intractable": [],
        }
        self.sorted_types = {"input": [], "other": []}
        self.possible_keywords = POSSIBLE_KEYWORDS.get("checkbox")
        self.possible_checkboxes = dict()
        self._main()

    # @_main_with_iframe
    def _main(self):
        locator_elements = self._collect_buttons()
        self._filter(locator_elements)
        if not self.buttons["buttons"]:
            self.result["status"] = "NOELEMENTS"
            self.result["message"] = "No checkbox elements"
            self.result["elements"] = []
        else:
            self.set_pass_status()
            self._sort_input()
            print("\n_sort_input")
            print("buttons", self.buttons["buttons"].__len__())
            # print("self.sorted_types", self.sorted_types)
            self.possible_checkboxes = {btn: [btn] for btn in self.buttons["buttons"]}
            Element.safe_foreach(self.sorted_types["input"], self._mark_native_inputs)
            # print("\nsorted input _mark_native_inputs", self.buttons["buttons"])
            Element.safe_foreach(self.sorted_types["other"], self.detect_possible_checkbox)
            # print("\nsorted other _possible_checkbox", self.buttons["buttons"])
            self._push_dependency()

    def _collect_buttons(self):
        """
        Collect all active elements that might be buttons using element locator.
        Set result status from "NOELEMENTS" to "PASS".
        Call purpose check
        """
        print("\n_collect_buttons")
        locator_required_elements = [
            "DIV",
            "INPUT",
            "LABEL",
            "BUTTON",
            "SPAN",
            "A",
            "IMG",
        ]
        self.driver.execute_script(locator_visible_script, locator_required_elements)

        locator_elements = self.driver.execute_script("return window.locatorVisible;")
        locator_elements = [Element(elem, self.driver) for elem in locator_elements]
        self._fix_selectors(locator_elements)
        # print("\nlocator_elements", locator_elements)
        return locator_elements

    def _click_sort(self, element):
        """
        Sort active elements for possible buttons by clicking
        """
        print("\n_click_sort")
        print("element", element)
        if element.tag_name == "input" and self.get_attribute(element, "type") == "checkbox":
            print("input checkbox")
            self.buttons["possible_buttons"].append(element)
            return
        if element.tag_name == "a":
            href = self.get_attribute(element, "href")
            # hyperlink with href, not anchor
            if href and re.match(r"^\w+|\/\w+", href):
                # print("\n!!!link!!!")
                return
        self.scroll_to_el(element)
        try:
            action = element.click(self.driver)["action"]
            # ! NONINTERACTABLE is triggered by input checkboxes at
            # * https://a11y-guidelines.orange.com/en/web/components-examples/listbox-with-checkboxes/
            if action == "NONINTERACTABLE":  # check overlapping
                self.activity.get(self.driver)
                action = element.click(self.driver)["action"]
            if action == "NONE":
                # tricky use later in style_diff (after remove)
                self.buttons["possible_buttons"].append(element)
            # pagechange or alert or newtab or lostelementexception
            elif action != "NONINTERACTABLE":
                self.buttons["links"].append(element)
                self.activity.get(self.driver)
            else:
                self.buttons["non_intractable"].append(element)
            print("action", action)
        except (
            InvalidArgumentException,
            StaleElementReferenceException,
            ElementLostException,
            NoSuchElementException,
        ) as e:
            print("exception", e)
            pass

    def _sort_input(self):
        for element in self.buttons["buttons"]:
            try:
                self.sorted_types[element.tag_name].append(element)
            except KeyError:
                self.sorted_types["other"].append(element)

    def _update_checkboxes(self, old: list, new: list):
        new = [cb.get_selector() for cb in new]
        for cb in old:
            if cb.get_selector() not in new:
                del self.possible_checkboxes[cb]

    def _push_dependency(self):
        """
        Method to finally sort out checkboxes, remove outer level copies.
        """
        print("\nself.possible_checkboxes", len(list(self.possible_checkboxes.keys())))
        position_old = list(self.possible_checkboxes.keys())
        position_cleaned = self._last_checkboxes_filter(list(self.possible_checkboxes.keys()))
        self._update_checkboxes(position_old, position_cleaned)
        print("\nself.possible_checkboxes final", len(list(self.possible_checkboxes.keys())))
        print("\nBASE RESULT\n", self.possible_checkboxes)
        self.result["dependency"] = self.possible_checkboxes

    def _filter(self, locator_elements: list):
        """Filter elements to avoid spare clickables
        :param clickable_elements: list of active UI elements
        """
        print("\n_filter")
        first_filter = self._text_filter(locator_elements)
        filter_result = self._nesting_filter(first_filter)
        print("\nfilter_result", len(filter_result))
        print("\nfilter_result", filter_result)
        Element.safe_foreach(filter_result, self._click_sort)
        print("\n_click_sort result", self.buttons["possible_buttons"])
        for element in self.buttons["possible_buttons"]:
            self.buttons["buttons"].append(element)
        self.buttons["possible_buttons"] = []
        self.buttons["links"] = []
        self.buttons["non_intractable"] = []

    def _last_checkboxes_filter(self, elements: list):
        """Filter elements again - after checkbox verification.
        Remain that contain not more than one of the others.
        If one indeed, remove that one inside.
        :param elements: list of genuine checkboxes elements
        :return list: smallest elements at positions or elements which cannot have child elements
        """
        print("\n_last_checkboxes_filter")
        filtered_elements = elements[:]
        for element in elements:
            try:
                descendants = element.find_by_xpath("descendant::*", self.driver)
                descendants = set(descendants).intersection(self.possible_checkboxes.keys())
            except (
                StaleElementReferenceException,
                ElementLostException,
                NoSuchElementException,
            ):
                continue
            if not descendants:
                continue
            elif len(descendants) > 1:
                filtered_elements.remove(element)
            else:
                only_child = descendants.pop()
                filtered_elements.remove(only_child)
        print("filtered_elements", filtered_elements)
        return filtered_elements

    def _attributes_string(self, element):
        """
        Created to avoid nav menu buttons, don't see another way for now
        """
        element = element.get_element(self.driver)

        return self.driver.execute_script(
            """
            var elem = arguments[0];
            var attrString = [];
            [...elem.attributes].forEach((attr) => { attrString.push(attr.value); });
            return attrString.join(' ');
        """,
            element,
        )

    def _nesting_filter(self, elements: list):
        """Remove parent elements like <div> of the clickable element,
        with the same tag name.
        Then remove child elements from filtered.
        :param elements: list of framework elements
        :return: list of framework elements
        """
        print("\n_nesting_filter")
        filtered_elements = list()
        for index, element in enumerate(elements):
            try:
                descendants = element.find_by_xpath("descendant::*", self.driver)
            except (
                StaleElementReferenceException,
                ElementLostException,
                NoSuchElementException,
            ):
                continue
            if not descendants:
                filtered_elements.append(element)
                continue
            descendants = [elem.get_selector() for elem in descendants]
            name = element.tag_name
            initial_elements = elements[:]
            initial_elements.pop(index)
            have_descendants = False
            for other_element in initial_elements:
                if other_element.get_selector() in descendants and other_element.tag_name == name:
                    have_descendants = True
                    break
            if not have_descendants:
                filtered_elements.append(element)

        child_filtered_elements = filtered_elements[:]
        for index, element in enumerate(filtered_elements):
            if element.tag_name in ("div", "span", "a"):
                continue
            try:
                descendants = element.find_by_xpath("descendant::*", self.driver)
            except (
                StaleElementReferenceException,
                ElementLostException,
                NoSuchElementException,
            ):
                continue
            descendants = [elem.get_selector() for elem in descendants]
            initial_elements = filtered_elements[:]
            initial_elements.pop(index)
            for other_element in initial_elements:
                if other_element.get_selector() in descendants:
                    child_filtered_elements = [
                        elem
                        for elem in child_filtered_elements
                        if elem.get_selector() != other_element.get_selector()
                    ]
        # print("child_filtered_elements", child_filtered_elements)
        return child_filtered_elements

    def _text_filter(self, elements: list):
        """Remove <div> elements which are text
        :param elements: list of active UI elements
        :return: list of framework elements
        """
        print("\n_text_filter")
        filtered_elements = list()
        for element in elements:
            if element.tag_name in ("div", "span", "button", "a"):
                html = element.source
                attributes = self._attributes_string(element)
                if re.search(r"<code>|<br>", html):
                    continue
                elif not re.search(self.possible_keywords, html):
                    """
                    Strong restriction. Reason - locator detects intractable (clickable)
                    text and there is no way to filter it.
                    """
                    continue
                elif re.search(r"nav", attributes):
                    """
                    Button is marked as nav button - can't be any of checkbox.
                    """
                    continue
            elif element.tag_name == "img":
                if element.get_parent(self.driver).tag_name == "a":
                    continue
            filtered_elements.append(element)

        # print("filtered_elements", filtered_elements)
        return filtered_elements

    def _fix_selectors(self, elements):
        for elem in elements:
            if elem.get_selector().find("#") != -1:
                elem.selector = _fix_numeral_selector(elem.get_selector())

    def _mark_native_inputs(self, element, value="checkbox"):
        """
        Mark native checkboxes or radio and so on as correct / incorrect
        """
        if element.get_element(self.driver).get_attribute("type") == value:
            return True
        if element in self.possible_checkboxes:
            del self.possible_checkboxes[element]
        return False

    def detect_possible_checkbox(self, element):
        """
        Detect elements which acts like checkbox.
        It can contain input checkbox
        or have ::before ::after style
        or change itself, page source by clicking there and back again
        It might be a checkbox, toggle button, menu button, select button.
        """
        try:
            input_child = element.find_by_xpath(".//input", self.driver)
            self._fix_selectors(input_child)
        except (
            StaleElementReferenceException,
            ElementLostException,
            NoSuchElementException,
        ):
            input_child = []
        if len(input_child) > 1:
            del self.possible_checkboxes[element]
            return
        if any(self._mark_native_inputs(child) for child in input_child):
            self.possible_checkboxes[element].extend(input_child)
            return
        if any(
            self._mark_native_inputs(child, value="radio") or self._mark_native_inputs(child, value="range")
            for child in input_child
        ):
            del self.possible_checkboxes[element]
            return
        # much faster if pass
        if self._markup_onclick_action(element):  # very tricky selector BUG everywhere
            return
        try:
            children = element.find_by_xpath("./descendant::*", self.driver)
            self._fix_selectors(children)
        except (
            StaleElementReferenceException,
            ElementLostException,
            NoSuchElementException,
        ):
            children = []
        # TODO dropdowns, popups filter, now solved by text_filter - button keyword exclude
        Element.safe_foreach(children + [element], self._click_sort)
        if self.buttons["links"]:  # pagechange / redirect among chilren
            self.buttons["links"] = []
            self.buttons["possible_buttons"] = []
            self.buttons["non_intractable"] = []
            del self.possible_checkboxes[element]
            return
        style_diff = None
        actions = ["NONE"] * len(self.buttons["possible_buttons"])
        actions += ["NONINTERACTABLE"] * len(self.buttons["non_intractable"])
        self.buttons["non_intractable"].extend(self.buttons["possible_buttons"])
        self.buttons["possible_buttons"] = []
        # go bottom up
        for child, action in zip(self.buttons["non_intractable"][::-1], actions):
            style_diff = style_diff or self._style_before_after(child, action)
            if style_diff:
                self.possible_checkboxes[element].append(child)
                self.buttons["non_intractable"] = []
                return
        self.buttons["non_intractable"] = []
        del self.possible_checkboxes[element]

    # takes 10x more time for checkbox identification, if invoked
    def _style_before_after(self, element: Element, action):
        """
        Compares all css attributes of element,
        ::before pseudo of it, and ::after pseudo of it
        :return: set of diverse css values in "pseudo wrap"
        UPD!
        Compares css attributes from children, after click for clickable,
        for others do as written earlier, separates on :action:
        """
        style_diff = set()
        if action != "NONE":
            return
        # go bottom up
        original, before, after = {}, {}, {}
        for elem in self.buttons["non_intractable"][::-1]:
            style_script = f"return window.getComputedStyle(document.querySelector('{elem.get_selector()}'));"
            original = self.driver.execute_script(style_script)
            element.click(self.driver)
            before = self.driver.execute_script(style_script)
            element.click(self.driver)
            after = self.driver.execute_script(style_script)
            before, after, original = map(lambda d: {k: str(v) for k, v in d.items()}, (before, after, original))
            onclick_diff = set(original.values()).symmetric_difference(before.values())
            if onclick_diff:  # or elem == element
                break
        before_diff = set(original.values()).symmetric_difference(before.values())
        after_diff = set(original.values()).symmetric_difference(after.values())
        # hardcoded empty drop filter
        before_diff = set(filter(lambda s: "" != s, before_diff))
        after_diff = set(filter(lambda s: "" != s, after_diff))
        if before_diff and not after_diff:
            style_diff = before_diff
        return style_diff

    def _markup_onclick_action(self, element: Element):
        """
        Compares some html with onclick changes,
        and on another click verifies changes rolled back
        :return: bool
        """
        body = self.driver.find_element_by_xpath("//body")
        parent = element.get_parent(self.driver)

        end_state = _drop_bad_attrs(element.get_element(self.driver).get_attribute("outerHTML"))
        parent_end_state = _drop_bad_attrs(get_element_opening_tag(parent.get_element(self.driver)))
        tree_end_state = len(body.get_attribute("innerHTML"))
        element.click(self.driver)

        revert_state = _drop_bad_attrs(element.get_element(self.driver).get_attribute("outerHTML"))
        parent_revert_state = _drop_bad_attrs(get_element_opening_tag(parent.get_element(self.driver)))
        tree_revert_state = len(body.get_attribute("innerHTML"))
        element.click(self.driver)

        second_end_state = _drop_bad_attrs(element.get_element(self.driver).get_attribute("outerHTML"))
        parent_second_end_state = _drop_bad_attrs(get_element_opening_tag(parent.get_element(self.driver)))
        tree_second_end_state = len(body.get_attribute("innerHTML"))

        if (
            element.get_element(self.driver).get_attribute("aria-checked") is not None
            or (end_state != revert_state and end_state == second_end_state)
            or (parent_second_end_state != parent_revert_state and parent_second_end_state == parent_end_state)
            or (tree_end_state != tree_revert_state and tree_end_state == tree_second_end_state)
        ):
            return True
        return False

    # disabled
    def _get_iframe(self):
        """
        Method returns iframe objects one by one
        to check for elements also inside iframe documents
        """
        iframes = self.locator.get_all_by_xpath(self.driver, "//iframe")
        for iframe in iframes:
            try:
                if visibility_of(iframe.get_element(self.driver))(self.driver):
                    yield iframe
            except (ElementLostException, StaleElementReferenceException):
                continue

    # disabled
    def _switch_to_iframe(self, iframe: Element, timeout=20):
        """
        Method implements switch to iframe
        After timeout, returns False
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, iframe.get_selector()))
            )
        except TimeoutException:
            return False
            # raise NameError(f'iframe {iframe} was not intractable after {timeout} sec')
        return True
