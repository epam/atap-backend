from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.test_pattern import SuperTest

__all__ = []

framework_version = 4
WCAG = "4.1.2"
name = "Ensure that menu elements have correct role"
depends = ["test_dd_detector"]
webdriver_restart_required = False
elements_type = "menu button"
test_data = [
    {
        "page_info": {"url": r"dropdowns/page_good_menu_button_1.html"},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"dropdowns/page_bugs_menu_2.html"},
        "expected_status": "FAIL"
    },
]
test_message = "Some menu buttons doesn't have appropriate ARIA role"
CORRECT_ROLES = [
    'menuitem',
    'menuitemcheckbox',
    'menuitemradio'
]


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
        Element.safe_foreach(list(self.elements_to_check.keys()), self._role_check)

    def _role_check(self, button):
        data = self.elements_to_check[button]
        if data["type"] != "menu":
            # print("NOT A MENU")
            return
        ul = self.get_ul(data["dd_elements"])
        li = self.get_li(data["dd_elements"])
        a = self.get_a(data["dd_elements"])
        if not ul or not li or not a:
            self.report_for_manual_check(button)
            return
        self.result["checked_elements"].append(button)

        if button.tag_name in ("button", "a") or self.get_attribute(button, "type") == "button":
            self.check_haspopup(button)
            self.check_tabindex_native(button)
            self.check_aria_expanded_true(button)
        else:
            self.check_tabindex_divlike(button)
            self.check_aria_expanded_false(button)

        self.check_button_role(button)
        if self.get_attribute(ul, 'role') == 'menu':
            self.check_roled_li_and_a(button, li, a)
        else:
            self.check_unroled_li_and_a(button, li, a)

    def activate_button(self, button):
        if self.elements_to_check[button]["click_activation"]:
            self._click_activation(button)
        elif self.elements_to_check[button]["kbd_activation"]:
            self._enter_activation(button)
        elif self.elements_to_check[button]["hover_activation"]:
            self._pointer_activation(button)

    def get_items(self, listholder: Element) -> list:
        list_items = listholder.find_by_xpath("descendant::li", self.driver)
        target_elements = []
        for item in list_items:
            a = item.find_by_xpath("descendant::a", self.driver) or []
            button = item.find_by_xpath("descendant::button", self.driver) or []
            target_elements.extend(a + button)
        if len(target_elements) >= len(list_items):
            return target_elements
        return list_items

    def check_haspopup(self, element):
        # WCAG 4.1.2
        if self.get_attribute(element, "aria-haspopup") != "true":
            self.report_issue(
                element=element,
                problem_message='A menu button have incorrect aria-haspopup attribute',
                error_id='MenuAriaHaspopup',
                severity="FAIL",
                test_message=test_message
            )

    def check_aria_expanded_true(self, element):
        # WCAG 4.1.2
        self.activate_button(element)
        if self.get_attribute(element, "aria-expanded") != "true":
            self.report_issue(
                element=element,
                problem_message='A menu button have incorrect aria-expanded attribute',
                error_id='MenuAriaExpanded',
                severity="FAIL",
                test_message=test_message
            )

    def check_aria_expanded_false(self, element):
        # WCAG 4.1.2 for disclosure buttons
        if self.get_attribute(element, "aria-expanded") != "false":
            self.report_issue(
                element=element,
                problem_message='A menu button have incorrect aria-expanded attribute for ',
                error_id='MenuAriaExpandedDisclosure',
                severity="FAIL",
                test_message=test_message
            )

    def check_tabindex_native(self, element):
        # WCAG 2.1.1 for (<button>, <a>, <input type='button'>)
        assert element.tag_name in ('button', 'a') or self.get_attribute(element, 'type') == 'button'
        if self.get_attribute(element, 'tabindex') == '-1':
            self.report_issue(
                element=element,
                problem_message='A menu button have incorrect tabindex attribute',
                error_id='MenuTabindex',
                severity="FAIL",
                test_message=test_message
            )

    def check_tabindex_divlike(self, element):
        # WCAG 2.1.1 for (<button>, <a>, <input type='button'>)
        assert element.tag_name in ('button', 'a') or self.get_attribute(element, 'type') == 'button'
        if self.get_attribute(element, 'tabindex') != '0':
            self.report_issue(
                element=element,
                problem_message='A menu button have incorrect tabindex attribute',
                error_id='MenuTabindex',
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

    def check_button_role(self, element):
        # WCAG 4.1.2
        if (element.get_parent(self.driver).tag_name == "li" and self.get_attribute(element, "role") not in
                CORRECT_ROLES) and self.get_attribute(element, "role") != "button":
            self.report_issue(
                element=element,
                problem_message='A menu button have incorrect role attribute',
                error_id='MenuButtonRole',
                severity="FAIL",
                test_message=test_message
            )

    def check_roled_li_and_a(self, button, li, a):
        # WCAG 4.1.2
        if not all(list(map(lambda item: self.get_attribute(item, "role") == 'none', li))) or \
                not all(list(map(lambda link: self.get_attribute(link, "role") in CORRECT_ROLES, a))):
            self.report_issue(
                element=button,
                problem_message='A menu button have incorrect items role attributes',
                error_id='MenuItemsNoRole',
                severity="FAIL",
                test_message=test_message
            )

    def check_unroled_li_and_a(self, button, li, a):
        # WCAG 4.1.2
        if any(list(map(lambda item: self.get_attribute(item, "role") == 'none', li))) or \
                any(list(map(lambda link: self.get_attribute(link, "role") in CORRECT_ROLES, a))):
            self.report_issue(
                element=button,
                problem_message='A menu button have incorrect items role attributes',
                error_id='MenuItemsExcessRole',
                severity="FAIL",
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
