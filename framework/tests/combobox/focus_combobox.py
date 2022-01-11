from string import ascii_lowercase, digits, punctuation, whitespace

from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException

from framework.element_locator import ElementLocator
from framework.element import ElementLostException
from framework.element import Element
from framework.libs.test_pattern import SuperTest

framework_version = 4
WCAG = "2.1.1"
name = "Ensures that navigation mechanism in combobox is accessible"
locator_required_elements = []
depends = ["test_combobox_role"]
webdriver_restart_required = True
elements_type = "combobox"
test_data = [
    {
        "page_info": {
            "url": r"combobox/page_good_combobox.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": r"combobox/page_bad_navigation_combobox.html"
        },
        "expected_status": "FAIL"
    }
]


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies):
    return NavigationTestCombobox(webdriver_instance, activity, element_locator, dependencies).get_result()


class NavigationTestCombobox(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.letters = ascii_lowercase + digits
        self.comboboxes = self.dependency_data[depends[0]]["dependency"]
        if self.comboboxes:
            self.set_pass_status()
        self._main()

    def _main(self):
        self.activity.get(self.driver)
        Element.safe_foreach(self.comboboxes, self._check_navigation)

    def _safe_clear(self, edit_field: Element):
        """ Safely clear the edit field's text.

        :param edit_field: An edit field to clear
        :return bool: True if succeed. False if element was lost.
        """
        try:
            edit_field.get_element(self.driver).clear()
            return True
        except StaleElementReferenceException:
            return False

    def _get_good_letter(self, field: Element, holder: Element):
        """ Return key by inputting which the holder have at least 2 elements to interact.
            Return empty string in other cases.
        """
        for key in self.letters:
            try:
                self._safe_clear(field)
                field.get_element(self.driver).send_keys(key)
            except (ElementNotInteractableException, ElementLostException):
                return ""
            current_childs = holder.find_by_xpath("child::*", self.driver)
            if len(current_childs) >= 2:
                self._safe_clear(field)
                return key
        return ""

    def _get_focus_able_elements(self, field: Element, holder: Element):
        """ Return focusable elements in the list and key to get them.

        """
        key = self._get_good_letter(field, holder)
        if not key:
            return None, None
        self._activate_element(element=field, method="Word", word=key)
        elements_in_the_list = holder.find_by_xpath("descendant::*", self.driver)
        focus_able_elements = list()
        for element in elements_in_the_list:
            self._page_refresh()
            self._activate_element(element=field, method="Word", word=key)
            if element.click(self.driver)["action"] != "NONINTERACTABLE":
                focus_able_elements.append(element)

        self._page_refresh()
        self._activate_element(element=field, method="Word", word=key)
        if len(holder.find_by_xpath("child::*", self.driver)) != len(focus_able_elements):
            focus_able_elements = self._filter_rows(field, focus_able_elements, key)
        return focus_able_elements, key

    def _filter_rows(self, field, focus_able_elements, key):
        """ Filter in case when one row in expanded list have multiple elements to click

        :param field:
        :param focus_able_elements:
        :param key:
        :return: list with first activateable elements in each row
        """
        if not focus_able_elements:
            return []
        for index, element in enumerate(focus_able_elements):
            try:
                elements_descendants = element.find_by_xpath("descendant::*", self.driver)
            except ElementLostException:
                continue
            step = 1
            for descendant in focus_able_elements[index+1::]:
                if descendant in elements_descendants:
                    step += 1
            if step > 1:
                break
        filtered_elements = focus_able_elements[::step]
        return filtered_elements

    def _check_navigation(self, data):
        """Check navigation behavior using some methods

        """
        field, holder = data
        self.result["checked_elements"].append(field)

        """ TODO
        1. if "readonly" - call readonly_check
           elif call space check / arrow check
           elif call key_input check
           else report bug (no keyboard mechanism)
        2. check navigation
        3. check selecting
        
        """

        focus_able_elements, key = self._get_focus_able_elements(field, holder)
        if not focus_able_elements:
            return
        # Have elements to focus
        self._text_check(field, focus_able_elements, key)

    def _text_check(self, field, focus_able_elements, key):
        """ text"""
        self._page_refresh()
        self._activate_element(element=field, method="Word", word=key)

        text_of_elements = self._get_focus_elements_text(focus_able_elements)
        current_focus = self._get_current_focus(field, key, text_of_elements)
        first_focus = current_focus
        temp = 0
        while text_of_elements[current_focus] != text_of_elements[-1]:
            if temp == 100:
                raise Exception("Unexpected behavior of focusing elements")
            temp += 1
            self._safe_clear(field)
            self._activate_element(element=field, method="Word", word=key + Keys.ARROW_DOWN * temp)
            current_focus = self._get_current_focus(field, key, text_of_elements)
            if current_focus == first_focus and current_focus is not 0:
                self.result["status"] = "FAIL"
                self.result["message"] = "Some comboboxes have inaccessible navigation mechanism"
                self.result["elements"].append({
                    "element": field,
                    "problem": "Unable to move focus in the combobox expanded list",
                    "error_id": "FocusMoving"
                })
                return
        self._safe_clear(field)
        self._activate_element(element=field, method="Word", word=key + Keys.ARROW_DOWN * (temp + 1))  # Must be first
        current_focus = self._get_current_focus(field, key, text_of_elements)
        if current_focus != 0 and current_focus is not False:
            self.result["status"] = "FAIL"
            self.result["message"] = "Some comboboxes have inaccessible navigation mechanism"
            self.result["elements"].append({
                "element": field,
                "problem": "Navigation in the combobox expanded list is not cycled",
                "error_id": "FocusLoop"
            })

    def _get_current_focus(self, field: Element, key, text_of_elements):
        """ Confirm current focus and returns the text of the gotten edit field.

        """
        self._activate_element(element=field, method="Enter")
        try:
            if field.tag_name in ("input", "textarea"):
                text = self._clear_str(field.get_element(self.driver).get_attribute("value"))
            else:
                text = self._clear_str(field.get_element(self.driver).text)
            if not text:
                raise Exception("No text in the edit field after input")  # possibly bad JS?
        except (StaleElementReferenceException, ElementLostException):
            raise Exception("Element was lost but shouldn't")

        focus = None
        if text == key:
            focus = False
        else:
            for index, elem_text in enumerate(text_of_elements):
                if text in elem_text:
                    focus = index
                    break
        if focus is not 0 and focus is None:
            raise Exception("Failed to focus the element")
        return focus

    def _get_focus_elements_text(self, focus_able_elements: list):
        text_of_elements = list()
        for element in focus_able_elements:
            text = self._clear_str(element.get_element(self.driver).text)
            text_of_elements.append(text)
        return text_of_elements

    @staticmethod
    def _clear_str(string: str):
        if not string:
            return ""
        cleared_str = ""
        for sign in string:
            if sign not in whitespace + punctuation:
                cleared_str += sign
        cleared_str.lower()
        return cleared_str
