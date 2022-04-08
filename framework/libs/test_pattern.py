""" There are classes to set up a base structure of tests

"""
from datetime import datetime
from typing import List, Optional

from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException, \
    MoveTargetOutOfBoundsException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from framework.activity import Activity
from framework.await_page_load import *
from framework.element import Element, ElementLostException
from framework.element_locator import ElementLocator
from framework.libs.html_tags import tags_lower

__all__ = ["SuperTest", "DetectingTest", "ListholderTest", "NavigationTest", "print_ex_time", "wrap_test_output"]


def print_elem(elements, tags_list):
    for element in elements:
        if element.tag_name in tags_list:
            print("$" * 40)
            print(element.source)


def print_ex_time(func):
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        print(f"Time to execute {func.__name__}:")
        print(datetime.now() - start_time, "seconds")
        return result
    return wrapper


def print_returned_result(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        try:
            if len(result) > 50:
                print(f"Returned result:\n{result[0:50:1]}\n...")
            else:
                print(f"Returned result:\n{result}")
        except (AttributeError, TypeError):
            print(f"Returned result:\n{result}")
        finally:
            print("")
        return result
    return wrapper


def wrap_test_output(test):
    def wrapper(*args, **kwargs):
        print("#" * 80, "{:^80}".format(f"START OF THE TEST"), "#" * 80, sep="\n")
        result = test(*args, **kwargs)
        print("#" * 80, "{:^80}".format("END OF THE TEST"), "#" * 80, sep="\n")
        return result
    return wrapper


class SuperTest:
    def __init__(self, webdriver_instance: webdriver, activity: Activity, locator: ElementLocator,
                 dependencies=None, **kwargs):
        """ Initialize standard class fields. Additionally set result status to "NOELEMENTS".

        :param webdriver_instance: A Selenium WebDriver statement
        :param activity: An activity on the page (If configured)
        :param locator: A framework's locator for getting elements
        :param dependencies: Data from other tests (default None)
        """
        self.locator = locator
        self.driver = webdriver_instance
        self.activity = activity
        self.dependency_data = dependencies
        self.actions = ActionChains(self.driver)
        self.result = {
            "status": "NOELEMENTS",
            "message": "There are no elements",
            "elements": [],
            "checked_elements": [],
            "dependency": [],
        }
        self.activity.get(self.driver)
        wait_for_page_load(self.driver)
        super().__init__(**kwargs)

    def scroll_to_el(self, element: Element) -> None:
        """Scroll the Web page to the received element."""
        element = element.get_element(self.driver)
        desired_y = (element.size['height'] / 2) + element.location['y']
        window_h = self.driver.execute_script('return window.innerHeight')
        window_y = self.driver.execute_script('return window.pageYOffset')
        current_y = (window_h / 2) + window_y
        scroll_y_by = desired_y - current_y
        self.driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)

    def focus_element(self, element: Element) -> None:
        """Set focus on the element."""
        selenium_element = element.get_element(self.driver)
        try:
            selenium_element.send_keys("")  # focus the element
        except ElementNotInteractableException:
            return
        current_element = self.driver.switch_to_active_element()
        assert current_element == selenium_element

    def reset_action_chains(self) -> None:
        """Create new ActionChains to avoid bugs."""
        self.actions = ActionChains(self.driver)

    def get_attribute(self, element: Element, attribute: str):
        return element.get_element(self.driver).get_attribute(attribute)

    def send_keys(self, element: Element, keys: str) -> None:
        element.get_element(self.driver).send_keys(keys)

    def get_result(self):
        return self.result

    def set_pass_status(self):
        self.result["status"] = "PASS"
        self.result["message"] = ""

    def _page_refresh(self):
        """ Completely refresh the page"""
        try:
            self.driver.refresh()
            self.activity.get(self.driver)
            wait_for_page_load(self.driver)
        except UnexpectedAlertPresentException:
            pass

    def get_rect(self, element: Element) -> dict:
        """Return a dictionary with the size and location of the element.
        Keys: "x", "y", "width", "height".
        Values: float numbers

        """
        return element.get_element(self.driver).rect

    def _activate_element(self, element: Element, method: str, word=""):
        """ Activate framework element with selected method.
        Methods are: "Pointer" -  Set mouse pointer at the middle of the element;
                     "Click" - Click on element;
                     "Enter" - Emulate pressing the Enter button;
                     "Word" - Emulate a specific word input.

        :param element: An framework Element to activate
        :param method: Activateable method (Pointer, Click, Enter, Word, Letters, Digits)
        :return: bool result of activation
        """
        self.scroll_to_el(element)
        if method == "Pointer":
            return self._pointer_activation(element)
        elif method == "Click":
            return self._click_activation(element)
        elif method == "Enter":
            return self._enter_activation(element)
        elif method == "Word":
            return self._word_activation(element, word)

    def _pointer_activation(self, element: Element) -> bool:
        """Activate element by setting mouse pointer at the middle of the element. Return result of activation."""
        self.reset_action_chains()

        try:
            is_element_displayed = element.get_element(self.driver).is_displayed()
            self.scroll_to_el(element)
        except ElementLostException:
            return False

        if not is_element_displayed:
            print("#" * 80)
            print("Failed to activate by pointer")
            print("Element is not displayed:")
            print(element.source)
            print("^" * 80)
            print()
            return False
        try:
            if not element.get_element(self.driver).is_displayed():
                return False
            sel_element = element.get_element(self.driver)
            self.actions.move_to_element(sel_element)
            self.actions.perform()
            time.sleep(3)  # Animation delay
        except (StaleElementReferenceException, MoveTargetOutOfBoundsException) as error:
            print("#" * 80)
            print("Failed to activate by pointer")
            print("Exception during action chains performing")
            print(error)
            print("^" * 80)
            print()
            return False
        return True

    def _click_activation(self, element: Element) -> bool:
        """ Activate element by clicking on the element

        :param element:
        :return: bool result of activation
        """
        try:
            element.click(self.driver)
            return True
        except Exception as bug:
            # print(bug)
            # print("At _click_activation - Click")
            return False

    def _enter_activation(self, element: Element) -> bool:
        """Activate element by emulating pressing the Enter button.

        :param element:
        :return: bool result of activation
        """

        try:
            self.focus_element(element)
            element.get_element(self.driver).send_keys(Keys.ENTER)
        except (ElementNotInteractableException, ElementLostException):
            return False

        return True

    def _word_activation(self, element, word):
        """ Activate element by emulating a specific word input

        :param element:
        :return: bool result of activation
        """
        if not word:
            raise ValueError("No word specified")
        self.focus_element(element)

        try:
            element.get_element(self.driver).send_keys(word)
        except Exception as fail_3:
            # print(f">>>>Cannot send {word}:\n", fail_3)
            return False

        return True

    def report_issue(self, element: Element, problem_message: str, error_id: str, severity: str,
                     test_message: str) -> None:
        self.result["status"] = "FAIL"
        self.result["message"] = test_message
        self.result["elements"].append({
            "element": element,
            "problem": problem_message,
            "error_id": error_id,
            "severity": severity,
        })

    @staticmethod
    def get_text(string: str) -> str:
        pattern = r">[^<]{1,}<"
        result_str = ""
        for sub_str in re.findall(pattern, string):
            result_str += sub_str.lower()[1:-1:]
        # print(f"TEXT OF THE {string[:7]}")
        # print(result_str)
        # print()
        return result_str


class DetectingTest(SuperTest):
    """ Is intended for tests which are requires detecting generating elements or elements with changeable sizes.

    """
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.zero_size_elements = list()  # constant
        self.buffer = list()  # mutable
        self.activity.get(self.driver)
        self.initial_elements = self._get_current_elements()
        Element.safe_foreach(self.initial_elements, self._get_zero_size_element)  # init constant list

    def _get_current_elements(self) -> List[Element]:
        """Collect all elements in the <body>."""
        try:
            current_elements = self.locator.get_all_by_xpath(self.driver, "//body//*")
        except UnexpectedAlertPresentException as bug:
            # print(">>>Unexpected behavior")
            raise bug
        return current_elements

    def _get_zero_size_element(self, element: Element):
        """ Append zero size element to the self.zero_size_elements"""
        rect = element.get_element(self.driver).rect

        if (rect["x"] == 0 and rect["y"] == 0) or (rect['height'] == 0 and rect["width"] == 0):
            self.zero_size_elements.append(element)

    def _get_zero_size_changed_elements(self) -> List[Element]:
        """ Find and return size changed elements using a buffer """
        self.buffer.clear()
        Element.safe_foreach(self.zero_size_elements, self._detect_changed_element)
        return self.buffer[:]

    def _detect_changed_element(self, element: Element):
        """Append size changed element to the self.buffer"""
        rect = element.get_element(self.driver).rect
        if (rect["x"] != 0 and rect["y"] != 0) and (rect['height'] != 0 and rect["width"] != 0):
            self.buffer.append(element)

    def _get_generated_elements(self) -> List[Element]:
        """Return a list with generated elements - elements which are new in the DOM tree.
        :return: generated_elements:
        """
        changed_html = self._get_current_elements()
        base_html = self.initial_elements[:]
        initial_positions_in_the_list = dict()
        new_elements_positions = dict()
        elements_in_initial_order = list()

        new_elements = list(set(changed_html) - set(base_html))  # break elements order

        for index, element in enumerate(changed_html):
            initial_positions_in_the_list.update({index: element})  # take initial order
        for key, value in initial_positions_in_the_list.items():
            if value in new_elements:
                new_elements_positions.update({key: value})  # get only new elements
        dict_keys = list(new_elements_positions.keys())  # take changed order
        dict_keys.sort()  # fix order
        for key in dict_keys:
            elements_in_initial_order.append(new_elements_positions[key])  # elements order is restored
        return elements_in_initial_order

    def _starts_with_tag(self, element: Element) -> Optional[bool]:
        """Return True if innerHTML starts with one of the html tags else False."""
        inner = element.get_element(self.driver).get_attribute("innerHTML")
        if not inner:
            return None
        for tag in tags_lower:
            opener = "<" + tag
            if inner.startswith(opener):
                return True
        return False


class ListholderTest(SuperTest):
    """Is intended for tests which are requires operations on listholders."""

    def _get_list_holder(self, data: tuple):
        """Find element which contain all other elements of the dropdown list"""
        button, elements, method = data
        # 1. Native selector
        if button.tag_name == "select":
            return button
        # 2. Native listholder
        self._page_refresh()
        self._activate_element(button, method)
        for element in elements:
            if element.tag_name == "ul":
                return element
        # 3. Other cases
        child_amount = {len(element.find_by_xpath("child::*", self.driver)): [] for element in elements}
        for element in elements:
            child_amount[len(element.find_by_xpath("child::*", self.driver))].append(element)
        holders = child_amount[max(child_amount.keys())]
        if len(holders) > 1:
            return None
        return holders[0]


class NavigationTest(SuperTest):
    """Is intended for tests which are requires navigation operations on dropdowns."""
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.activation_keys = (Keys.ARROW_DOWN, Keys.ARROW_UP, Keys.SPACE, Keys.ENTER)
        self.navigation_keys = (Keys.ARROW_DOWN, Keys.ARROW_UP, Keys.TAB)

    def get_keyboard_activation_key(self, button: Element, list_elements: list) -> str:
        """Return key by which a dropdown is activating. Otherwise, return empty string."""
        # Page refresh
        self.activity.get(self.driver)
        # Set focus on menu button
        self.focus_element(button)
        # Try to activate by keyboard
        selenium_button = button.get_element(self.driver)
        assert any(self.check_visibility(element) for element in list_elements) is False
        for key in self.activation_keys:
            selenium_button.send_keys(key)
            if any(self.check_visibility(element) for element in list_elements):
                return key
        return ""

    def check_focus_moving(self, button: Element, list_elements: list, nav_key: str,
                           activation_key: str = Keys.ENTER) -> bool:
        self.activity.get(self.driver)

        selenium_button = button.get_element(self.driver)
        selenium_button.send_keys(activation_key)

        # Check that next focused element in expanded window
        first_focused = self.focus_next_element(nav_key)

        if first_focused not in list_elements:
            return False

        # Check that focus successfully moved in expanded window
        next_focused = self.focus_next_element(nav_key)
        if (next_focused not in list_elements) and next_focused == first_focused:
            return False
        return True

    def check_visibility(self, element: Element) -> bool:
        """Check elements sizes. Return true if element is presented on page."""
        selenium_element = element.get_element(self.driver)
        rect = selenium_element.rect
        if (rect["x"] != 0 and rect["y"] != 0) and (rect['height'] != 0 and rect["width"] != 0):
            return True
        else:
            return False

    def focus_next_element(self, key) -> Optional[Element]:
        """ Move focus to the next element using received key.
        Return new focused element if focus was changed. Otherwise, return None.
        """
        start_element = self.driver.switch_to_active_element()
        start_element.send_keys(key)
        next_element = self.driver.switch_to_active_element()
        if start_element != next_element:
            return Element(next_element, self.driver)
        else:
            return None

    def append_error_message(self, bug_message: str, element: Element, element_problem_message: str,
                             error_id: str) -> None:
        self.result["status"] = "FAIL"
        self.result["message"] = bug_message
        self.result["elements"].append({
            "element": element,
            "problem": element_problem_message,
            "error_id": error_id
        })
