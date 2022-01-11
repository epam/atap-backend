from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.test_pattern import SuperTest

__all__ = []

framework_version = 4
WCAG = "4.1.2"
name = "Ensure that selector elements have correct role"
depends = ["test_dd_detector"]
webdriver_restart_required = False
elements_type = "selector"
test_data = [
    # {
    #     "page_info": {"url": r"dropdowns/page_good_selector_2.html"},
    #     "expected_status": "PASS"
    # },
    {
        "page_info": {"url": r"dropdowns/page_bugs_selector_listholder_role.html"},
        "expected_status": "FAIL"
    },
]
test_message = "Some menu buttons doesn't have appropriate ARIA role"


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return MenuRoleAndAttributes(webdriver_instance, activity, element_locator, dependencies).get_result()


class MenuRoleAndAttributes(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.elements_to_check = self.dependency_data[depends[0]]["dependency"]
        if not self.elements_to_check:
            return
        self.set_pass_status()
        self._main()

    def _main(self):
        Element.safe_foreach(list(self.elements_to_check.keys()), self._attr_check)

    def _attr_check(self, button):
        data = self.elements_to_check[button]
        if data["type"] not in ("selector", "action", "listbox", "selector_no_role"):
            return
        ul = self.get_ul(data["dd_elements"])
        li = self.get_li(data["dd_elements"])
        if not ul or not li:
            self.report_for_manual_check(button)
            return
        self.result["checked_elements"].append(button)

        if button.tag_name not in ("button", "select") and self.get_attribute(button, "role") != "button" \
                and self.get_attribute(button, "tabindex") == "0" \
                and self.get_attribute(button, "aria-haspopup") in ("true", "listbox", "menu") \
                and (data["type"] != "listbox" and self.get_attribute(button, "aria-expanded") == "false"):
            # 1. WCAG 4.1.2
            self.report_no_role(button)

        if data["type"] == "listbox" \
                and (button.tag_name in ("button", "select") or self.get_attribute(button, "role") == "button") \
                and self.get_attribute(button, "aria-haspopup") != "listbox" \
                and self.get_attribute(button, "tabindex") in ("0", None):
            # 2. WCAG 4.1.2
            self.report_haspopup_listbox(button)

        if data["type"] == "action" \
                and (button.tag_name in ("button", "select") or self.get_attribute(button, "role") == "button")\
                and self.get_attribute(button, "aria-haspopup") not in ("true", "menu") \
                and self.get_attribute(button, "tabindex") in ("0", None):
            # 4. WCAG 4.1.2
            self.report_haspopup_action(button)

        if (button.tag_name not in ("button", "select") or self.get_attribute(button, "role") != "button") \
                and (self.get_attribute(button, "aria-haspopup") not in ("true", "listbox", "menu") or
                     (data["type"] != "listbox" and self.get_attribute(button, "aria-expanded") != "false"))\
                and self.get_attribute(button, "tabindex") in ("0", None):
            # 5. WCAG 4.1.2
            self.report_no_role_and_attr(button)

        if (button.tag_name not in ("button", "select") or self.get_attribute(button, "role") != "button") \
                and (self.get_attribute(button, "aria-haspopup") not in ("true", "listbox", "menu") or
                     (data["type"] != "listbox" and self.get_attribute(button, "aria-expanded") != "false"))\
                and self.get_attribute(button, "tabindex") != "0":
            # 6 WCAG 4.1.2 and WCAG 2.1.1
            self.report_bad_aria(button)

        if button.tag_name not in ("button", "select") and self.get_attribute(button, "role") in ("button", "combobox")\
                and self.get_attribute(button, "tabindex") != "0":
            # 7. WCAG 2.1.1
            self.report_no_tabindex(button)

        if button.tag_name in ("button", "select") and self.get_attribute(button, "tabindex") == "-1":
            # 8. WCAG 2.1.1
            self.report_negative_tabindex(button)

        if button.tag_name != "select" \
                and self.get_attribute(button, "aria-haspopup") in ("true", "listbox", "menu")\
                and self.get_attribute(button, "tabindex") in ("0", None):
            self.check_aria_expanded_true(button)

    def report_bad_aria(self, element):
        self.report_issue(
            element=element,
            problem_message="A selector don't have aria attributes and have incorrect tabindex",
            error_id='SelectorBadAria',
            severity="FAIL",
            test_message=test_message
        )

    def report_no_role_and_attr(self, element):
        self.report_issue(
            element=element,
            problem_message="A selector don't have aria attributes",
            error_id='SelectorRoleAndAttr',
            severity="FAIL",
            test_message=test_message
        )

    def report_haspopup_action(self, element):
        self.report_issue(
            element=element,
            problem_message='A selector have incorrect aria-haspopup attribute',
            error_id='ActionMenuHaspopup',
            severity="FAIL",
            test_message=test_message
        )

    def report_haspopup_listbox(self, element):
        self.report_issue(
            element=element,
            problem_message='A selector have incorrect aria-haspopup attribute',
            error_id='ListboxHaspopup',
            severity="FAIL",
            test_message=test_message
        )

    def report_no_role(self, element):
        self.report_issue(
            element=element,
            problem_message="A selector don't have aria role",
            error_id='SelectorNoRole',
            severity="FAIL",
            test_message=test_message
        )

    def report_negative_tabindex(self, element):
        self.report_issue(
            element=element,
            problem_message="A selector have negative tabindex",
            error_id='SelectorNegativeTabindex',
            severity="FAIL",
            test_message=test_message
        )

    def report_no_tabindex(self, element):
        self.report_issue(
            element=element,
            problem_message="A selector don't have  tabindex",
            error_id='SelectorNoTabindex',
            severity="FAIL",
            test_message=test_message
        )

    def activate_button(self, button):
        if self.elements_to_check[button]["click_activation"]:
            self._click_activation(button)
        elif self.elements_to_check[button]["kbd_activation"]:
            self._enter_activation(button)
        elif self.elements_to_check[button]["hover_activation"]:
            self._pointer_activation(button)

    def check_aria_expanded_true(self, element):
        # 3. WCAG 4.1.2
        self.activate_button(element)
        if self.get_attribute(element, "aria-expanded") != "true":
            self.report_issue(
                element=element,
                problem_message='A selector have incorrect aria-expanded attribute',
                error_id='SelectorAriaExpanded',
                severity="FAIL",
                test_message=test_message
            )

    def report_for_manual_check(self, element):
        # WARN for manual check
        self.report_issue(
            element=element,
            problem_message='A menu button have unexpected realization',
            error_id='MenuManualCheck',
            severity="WARN",
            test_message=test_message
        )

    @staticmethod
    def get_ul(elements):
        for element in elements:
            if element.tag_name == "ul":
                return element

    @staticmethod
    def get_li(elements):
        li = [elem for elem in elements if elem.tag_name == "li"]
        return li

    @staticmethod
    def get_a(elements):
        a = [elem for elem in elements if elem.tag_name == "a"]
        return a
