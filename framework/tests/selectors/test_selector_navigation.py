from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from framework.element import Element
from framework.libs.test_pattern import NavigationTest


name = "Ensures that selectors support keyboard navigation mechanism"
locator_required_elements = []
framework_version = 4
WCAG = "2.1.1"
depends = ["test_dd_detector"]
webdriver_restart_required = False
elements_type = "selector"
test_data = [
    {
        "page_info": {"url": r"dropdowns/page_good_selector.html"},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"dropdowns/page_bugs_selector_no_keyboard.html"},
        "expected_status": "FAIL"
    },
]
bug_message = "Some selectors have incorrect navigation mechanism"
element_problem_message = "A selector doesn't support keyboard navigation"


def test(webdriver_instance: webdriver, activity, element_locator, dependencies=None):
    return SelectorNavMoving(webdriver_instance, activity, element_locator, dependencies).get_result()


class SelectorNavMoving(NavigationTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.select_keys = (Keys.ENTER, Keys.SPACE)
        self.elements_to_check = self.dependency_data[depends[0]]["dependency"]
        if self.elements_to_check:
            self.set_pass_status()
        self._main()

    def _main(self):
        Element.safe_foreach(list(self.elements_to_check.keys()), self._navigation_check)

    def _navigation_check(self, button):
        data = self.elements_to_check[button]
        if data["type"] not in ("selector", "action", "listbox", "combobox", "selector_no_role"):
            return

        visible_elements = self.elements_to_check[button]["dd_elements"]
        self.result["checked_elements"].append(button)
        if button.tag_name == "select":  # Native selectors can't be incorrect
            return

        activation_key = self.get_keyboard_activation_key(button, visible_elements)
        if not activation_key:
            self.append_error_message(bug_message, button, element_problem_message, "SelectorActivation")

        self._activate_element(button, "Word", activation_key)
        first_element = Element(self.driver.switch_to_active_element(), self.driver)
        first_element_state = first_element.get_element(self.driver).get_attribute("outerHTML")
        if first_element == button:
            first_element.get_element(self.driver).send_keys(Keys.ARROW_DOWN)
            first_element = Element(self.driver.switch_to_active_element(), self.driver)
            if first_element == button:
                self.append_error_message(bug_message, button, element_problem_message, "SelectorNavigation")
                return
        elif first_element not in visible_elements:
            raise Exception(
                f"FOCUSED ELEMENT NOT IN VISIBLE_AFTER_ACTIVATION ELEMENTS.\n"
                f"PAGE - {self.activity.url}\n"
                f"Fist element:\n"
                f"{first_element.source}"
            )
        first_element.get_element(self.driver).send_keys(Keys.ARROW_DOWN)
        second_element = Element(self.driver.switch_to_active_element(), self.driver)
        second_element_state = second_element.get_element(self.driver).get_attribute("outerHTML")
        if (second_element == first_element) and (second_element_state == first_element_state):
            if data["type"] in ("selector", "listbox"):
                self.append_error_message(bug_message, button, element_problem_message, "SelectorNavigation")
            elif data["type"] == "action":
                self.append_error_message(bug_message, button, element_problem_message, "ActionMenuNavigation")
            elif data["type"] == "combobox":
                self.append_error_message(bug_message, button, element_problem_message, "ComboboxNavigation")
            elif data["type"] == "selector_no_role":
                self.append_error_message(bug_message, button, element_problem_message, "NoRoleSelectorNavigation")
            return
        elif second_element not in visible_elements:
            raise Exception(
                f"FOCUSED ELEMENT NOT IN VISIBLE_AFTER_ACTIVATION ELEMENTS.\nPAGE - {self.activity.url}")

        # if not any(self.check_selecting(button, activation_key, conformation_key)
        #            for conformation_key in self.select_keys):
        #     self.append_error_message(bug_message, button, element_problem_message, "SelectorConfirmation")

    def get_selected_text(self, element: Element):
        """Return text value of the element

        """
        selenium_element = element.get_element(self.driver)
        return selenium_element.text

    def check_selecting(self, button: Element, activation_key: str, conformation_key: str):
        self.activity.get(self.driver)
        self.focus_element(button)

        start_text = self.get_selected_text(button)

        selenium_button = button.get_element(self.driver)
        selenium_button.send_keys(activation_key)

        current_element = Element(self.driver.switch_to_active_element(), self.driver)
        if current_element == button:
            current_element.get_element(self.driver).send_keys(Keys.ARROW_DOWN)

        current_element.get_element(self.driver).send_keys(Keys.ARROW_DOWN)
        current_element.get_element(self.driver).send_keys(conformation_key)

        end_text = self.get_selected_text(button)
        try:
            assert start_text != end_text
        except AssertionError:
            return False
        return True
