from string import digits
from time import sleep
import re

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.test_pattern import DetectingTest

__all__ = []

framework_version = 4
WCAG = "4.1.2"
name = "Ensures that combobox have appropriate role"
locator_required_elements = []
depends = ["test_buttons_purpose"]
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
            "url": "combobox/page_bug_combobox.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": r"combobox/page_bad_navigation_combobox.html"
        },
        "expected_status": "FAIL"
    },
]

NON_EDIT_FIELD_TYPES = ("button", "checkbox", "file", "hidden", "image", "radio", "reset", "submit")
TEST_MESSAGE = "Some comboboxes have incorrect role and/or doesn't able to receive focus using keyboard"
TOLERANCE_X = 10.0
TOLERANCE_WIDTH = 20.0


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies):
    return ComboboxTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class ComboboxTest(DetectingTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.start_page = self.driver.current_url
        self.checkable_elements = dict()
        self.letters = "aeiouy" + digits
        self._main()

    def _main(self):
        self.activity.get(self.driver)
        self._collect_elements()
        self._detect_comboboxes()
        if any(self.checkable_elements[element]["is_combobox"] for element in list(self.checkable_elements.keys())) and\
                self.result["status"] != "FAIL":
            self.set_pass_status()
        Element.safe_foreach(list(self.checkable_elements.keys()), self.check_keyboard_support)
        Element.safe_foreach(list(self.checkable_elements.keys()), self.checks)

    def _collect_elements(self):
        """ Collect all edit fields which are potentially might be comboboxes."""
        activateable_elements = self.dependency_data[depends[0]]["dependency"]
        Element.safe_foreach(activateable_elements, self.prepare_combobox_data)

    def prepare_combobox_data(self, element):
        """Take only edit fields from dependency and prepare a data"""
        element_data = {
            "tag": element.tag_name,
            "type": element.get_element(self.driver).get_attribute("type"),
            "contenteditable": element.get_element(self.driver).get_attribute("contenteditable")
        }
        if element_data["tag"] == "textarea" or \
                (element_data["tag"] == "input" and element_data["type"] not in NON_EDIT_FIELD_TYPES) or \
                element_data["contenteditable"] == "true":
            self.checkable_elements[element] = dict(
                readonly=self.is_readonly(element),
                role=self.find_combobox_role(element),
                generated_elements=[],
                size_changed_elements=[],
                method=None,
                letter=None,
                listholder=None,
                is_combobox=False,
                keyboard_support=False,
                have_dd_element=False,
            )

    def is_readonly(self, element: Element):
        """Return True if element have aria-readonly or readonly attribute. Otherwise return False"""
        element = element.get_element(self.driver)
        if element.get_attribute("aria-readonly") or element.get_attribute("readonly"):
            return True
        return False

    def _detect_comboboxes(self):
        checkable_elements = list(self.checkable_elements.keys())
        Element.safe_foreach(checkable_elements, self._interact_check)
        checkable_elements = list(self.checkable_elements.keys())
        Element.safe_foreach(checkable_elements, self._detect_list_holders)
        Element.safe_foreach(checkable_elements, self.prepare_letter_type_comboboxes_data)

    def clear_field(self, edit_field: Element):
        edit_field.get_element(self.driver).clear()

    def _interact_check(self, element: Element):
        """Check an element behavior to ensure that it is a combobox"""
        if self.checkable_elements[element]["readonly"]:
            self.check_readonly_combobox(element)
        else:
            self.check_standard_combobox(element)

    def check_readonly_combobox(self, element: Element):
        """Check that an edit field with "readonly" attribute is a combobox"""
        if not self.check_arrow_down_activation(element):
            if not self.check_space_activation(element):
                self.check_click_activation(element)

    def check_standard_combobox(self, element: Element):
        if not self.check_letter_input_activation(element):
            if not self.check_arrow_down_activation(element):
                if not self.check_click_activation(element):
                    self.check_keyword(element)

    def check_letter_input_activation(self, element: Element):
        """Check that a combobox can be activated by letter input"""
        self._page_refresh()
        data = self.checkable_elements[element]
        if self.get_attribute(element, "type") in ("tel", "number"):
            keys = digits
        else:
            keys = "aeiouy"
        self.focus_element(element)
        for letter in keys:
            self.send_keys(element, letter)

            self.check_for_size_changed_elements(element)
            self.check_for_generated_elements(element)
            self.detect_any_dropdown_like_element(element)

            if len(data["size_changed_elements"]) >= 2 or len(data["generated_elements"]) >= 2:
                self.checkable_elements[element]["method"] = "Letter"
                self.checkable_elements[element]["letter"] = letter
                return True

            self.clear_field(element)

        return False

    def check_arrow_down_activation(self, element):
        """Check that a combobox can be activated by pressing the "arrow_down" key"""
        self._page_refresh()
        if self._activate_element(element, "Word", Keys.ARROW_DOWN):
            if self.check_potential_combobox_data(element):
                self.checkable_elements[element]["method"] = "Arrow"
                self.checkable_elements[element]["letter"] = Keys.ARROW_DOWN
                return True

    def check_space_activation(self, element):
        """Check that a combobox can be activated by pressing the "space" key"""
        self._page_refresh()
        if self._activate_element(element, "Word", Keys.SPACE):
            if self.check_potential_combobox_data(element):
                self.checkable_elements[element]["method"] = "Space"
                self.checkable_elements[element]["letter"] = Keys.SPACE
                return True

    def check_click_activation(self, element):
        """Check that a combobox can be activated by clicking on it"""
        self._page_refresh()
        if self._activate_element(element, "Click"):
            if self.check_potential_combobox_data(element):
                self.checkable_elements[element]["method"] = "Click"
                return True

    def check_keyword(self, element):
        """Check that an input field is an undetectable combobox by keyword existence"""
        if element.source.count("combo"):
            self.checkable_elements.pop(element)
            self.report_keyboard_activation_mechanism(element, severity="WARN")
            if not self.find_combobox_role(element):
                self.report_bad_role(element, severity="WARN")

    def _detect_list_holders(self, element: Element):
        """Detect list holder (like <ul>) which are a part of combobox"""
        field_data = self.checkable_elements[element]
        if field_data["listholder"]:
            field_data["is_combobox"] = True
            return

        list_items = field_data["generated_elements"] or field_data["size_changed_elements"]
        if not list_items:
            field_data["is_combobox"] = False
            return

        if field_data["method"] == "Click":
            self._activate_element(element, "Click")
        else:
            self._activate_element(element, field_data["method"], field_data["letter"])

        # Case with one element
        if len(list_items) == 1:
            if not self._starts_with_tag(list_items[0]):  # generated single list item
                list_holder = list_items[0].get_parent(self.driver)
                field_data["listholder"] = list_holder
            else:  # list holder has changed its own sizes
                field_data["listholder"] = list_items[0]
            field_data["is_combobox"] = True
            return

        list_holder_detected = False
        for index, element in enumerate(list_items[-1::-1]):
            if list_holder_detected:
                break
            element_rect = element.get_element(self.driver).rect
            position_1 = index + 1

            if not self._starts_with_tag(element):  # text detected, it's in the index position
                for index_2, second_element in enumerate(list_items[-1 - position_1::-1]):
                    if list_holder_detected:
                        break
                    second_element_rect = second_element.get_element(self.driver).rect
                    if not self._starts_with_tag(second_element) and (
                            second_element_rect['x'] == element_rect['x'] or
                            second_element_rect['width'] == element_rect['width']):
                        # filter in case when text in multiple <spans> in one selector option

                        # second text detected, it's index_2
                        if index_2 == 0:  # case when list items have the same parent
                            list_holder_detected = True
                            list_holder = list_items[-position_1].get_parent(self.driver)
                            field_data["listholder"] = list_holder
                            field_data["is_combobox"] = True
                            break

                        else:
                            for meter in range(index_2):
                                position_2 = position_1 + index_2 + 1 + meter
                                previous_parent = list_items[-position_2]
                                descendants = previous_parent.find_by_xpath("descendant::*", self.driver)

                                if element in descendants:
                                    # for case when list items in few divs and list holder is far away
                                    list_holder_detected = True
                                    list_holder = previous_parent.get_parent(self.driver)
                                    field_data["listholder"] = list_holder
                                    field_data["is_combobox"] = True
                                    break

    def find_combobox_role(self, element):
        """Check that input field or it's parent div have role combobox"""

        parent_0 = element.get_parent(self.driver)
        parent_1 = parent_0.get_parent(self.driver)
        parent_2 = parent_1.get_parent(self.driver)
        if element.get_attribute(self.driver, "role") == "combobox" or \
                parent_0.get_attribute(self.driver, "role") == "combobox" or \
                parent_1.get_attribute(self.driver, "role") == "combobox" or \
                parent_2.get_attribute(self.driver, "role") == "combobox":
            return "combobox"
        return ""

    def check_potential_combobox_data(self, element: Element):
        """Look for signs that an element is a combobox"""
        self.check_for_generated_elements(element)
        self.check_for_size_changed_elements(element)
        if (self.checkable_elements[element]["generated_elements"] or
                self.checkable_elements[element]["size_changed_elements"]):
            self.detect_any_dropdown_like_element(element)
            return True

    def check_for_generated_elements(self, element):
        """Check that there are new elements"""
        generated_elements = self._get_generated_elements()
        if generated_elements:
            self.checkable_elements[element]["generated_elements"] = generated_elements
            if not self.checkable_elements[element]["listholder"]:
                self.checkable_elements[element]["listholder"] = self.try_to_find_ul(generated_elements)
            return True

    def check_for_size_changed_elements(self, element):
        """Check that there are elements which are was hidden"""
        size_changed = self._get_zero_size_changed_elements()
        if size_changed:
            self.checkable_elements[element]["size_changed_elements"] = size_changed
            if not self.checkable_elements[element]["listholder"]:
                self.checkable_elements[element]["listholder"] = self.try_to_find_ul(size_changed)
            return True

    def try_to_find_ul(self, elements: list):
        if elements[0].tag_name == "li":
            holder = elements[0].find_by_xpath("ancestor::ul", self.driver)[0]
            if holder:
                return holder
        for element in elements:
            if element.tag_name == "ul":
                return element

    def checks(self, field: Element):
        data = self.checkable_elements[field]
        if data["is_combobox"]:
            self.result["checked_elements"].append(field)
            # 4.1.2
            if data["role"] != "combobox":
                self.report_bad_role(field)

            # 2.1.1
            if data["method"] == "Click":
                self.report_keyboard_activation_mechanism(field)
            if data["keyboard_support"] is False:
                self.report_focus(field)
        elif data["have_dd_element"]:
            self.report_possible_broken_combo(field, "WARN")

    def report_possible_broken_combo(self, element, severity="FAIL"):
        self.report_issue(
            element=element,
            problem_message="The element in not detected as combobox. Element should be checked manually",
            error_id="ComboboxBroken",
            severity=severity,
            test_message=TEST_MESSAGE,
        )

    def report_bad_role(self, element, severity="FAIL"):
        self.report_issue(
            element=element,
            problem_message="The element have incorrect role",
            error_id="ComboboxRole",
            severity=severity,
            test_message=TEST_MESSAGE,
        )

    def report_keyboard_activation_mechanism(self, element, severity="FAIL"):
        self.report_issue(
            element=element,
            problem_message="The element don't support keyboard activation",
            error_id="ComboboxNoKeyboardSupport",
            severity=severity,
            test_message=TEST_MESSAGE,
        )

    def report_focus(self, element, severity="FAIL"):
        self.report_issue(
            element=element,
            problem_message="Unable to move focus in the combobox expanded list",
            error_id="ComboboxKeyboardMechanism",
            severity=severity,
            test_message=TEST_MESSAGE,
        )

    def prepare_letter_type_comboboxes_data(self, field: Element):
        if self.checkable_elements[field]["method"] == "letter":
            self.find_at_least_two_listitems(field)

    def find_at_least_two_listitems(self, field: Element):
        """Find a letter by input which there are at least two elements to focus in the dropdown list"""
        combobox_data = self.checkable_elements[field]
        self._page_refresh()
        for key in self.letters:
            self.clear_field(field)
            self.send_keys(field, key)

            current_childs = combobox_data["listholder"].find_by_xpath("child::*", self.driver)
            if len(current_childs) >= 2:
                self.clear_field(field)
                combobox_data["letter"] = key
                break

    def _get_current_focus(self, field: Element):
        """Confirm current focus and returns the text of the gotten edit field"""
        self.send_keys(field, Keys.ENTER)
        if field.tag_name in ("input", "textarea"):
            text = self.get_attribute(field, "value").lower()
        else:
            text = field.get_element(self.driver).text.lower()
        if not text:
            raise Exception("No text in the edit field after input")
        if text == self.checkable_elements[field]["letter"]:
            return None

        for index, elem_text in enumerate(self.checkable_elements[field]["list_items_text"]):
            if text in elem_text:
                return index

    def get_list_items_text(self, listholder: Element):
        childs = listholder.find_by_xpath("child::*", self.driver)
        text_of_elements = [self.get_text(self.get_attribute(element, "outerHTML")) for element in childs]
        assert len(text_of_elements) >= 2
        return text_of_elements

    def check_keyboard_support(self, field: Element):
        data = self.checkable_elements[field]
        if data["method"] in ("Click", None) or data["listholder"] is None:
            return
        self._page_refresh()
        letter = data["letter"]
        self.scroll_to_el(field)
        self.send_keys(field, letter)
        sleep(1)
        data["list_items_text"] = self.get_list_items_text(data["listholder"])
        current_focus = self._get_current_focus(field)
        first_focus = current_focus

        if data["readonly"]:
            self._page_refresh()
        else:
            self.clear_field(field)
        self.send_keys(field, letter)
        sleep(0.5)
        self.send_keys(field, Keys.ARROW_DOWN)

        current_focus = self._get_current_focus(field)
        if current_focus != first_focus:
            data["keyboard_support"] = True
        else:
            self.check_for_false_detect(field, data, letter)

    def check_for_false_detect(self, field: Element, data, letter):
        list_items = data["listholder"].find_by_xpath("child::*", self.driver)[0:6]
        for list_item in list_items:
            self._page_refresh()
            self.send_keys(field, letter)
            sleep(1)
            possible_clickable = list_item.find_by_xpath("descendant-or-self::*", self.driver)
            for element in possible_clickable:
                element.click(self.driver)
                if self.start_page != self.driver.current_url:
                    data["is_combobox"] = False
                    return

    def detect_any_dropdown_like_element(self, element: Element):
        """Check case when combobox have incorrect implementation.
        Mark element as combobox-like for manual check."""
        data = self.checkable_elements[element]
        rect = self.get_rect(element)
        for index, elem in enumerate(data["generated_elements"] + data["size_changed_elements"]):
            assert index < 30  # If Exception - recalculate tolerance and check combo UX/UI
            elem_rect = self.get_rect(elem)
            # First condition (all) is True if element is presented
            if all(elem_rect.values()) and rect["x"] - TOLERANCE_X <= elem_rect["x"] <= rect["x"] + TOLERANCE_X and \
                    rect["width"] - TOLERANCE_WIDTH <= elem_rect["width"] <= rect["width"] + TOLERANCE_WIDTH:
                data["have_dd_element"] = True
                break
