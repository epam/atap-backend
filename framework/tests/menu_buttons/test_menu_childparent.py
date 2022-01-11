from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.test_pattern import SuperTest

__all__ = []

framework_version = 4
WCAG = "4.1.2"
name = "Ensure that menu button have correct role"
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
test_message = "Some menu buttons have incorrect child-parent realisation"
CORRECT_ROLES = [
    'menuitem',
    'menuitemcheckbox',
    'menuitemradio'
]


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return MenuButtonRole(webdriver_instance, activity, element_locator, dependencies).get_result()


class MenuButtonRole(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.elements_to_check = self.dependency_data[depends[0]]["dependency"]
        if self.elements_to_check:
            self.set_pass_status()
        self._main()

    def _main(self):
        Element.safe_foreach(list(self.elements_to_check.keys()), self._check)

    def _check(self, button: Element):
        data = self.elements_to_check[button]
        if data["type"] != "menu":
            return
        self.result["checked_elements"].append(button)
        ul = self.get_ul(data["dd_elements"])
        assert ul is not None
        li = self.get_li(data["dd_elements"])
        assert li is not None
        a = self.get_a(data["dd_elements"])
        assert a is not None

        # 4.1.2
        if self.get_attribute(ul, "role") != "menu" or \
                any(map(lambda x: self.get_attribute(x, "role") != 'none', li)) or \
                any(map(lambda x: self.get_attribute(x, "role") not in CORRECT_ROLES, a)):
            self.report_issue(
                button,
                "Navigation menu does not have proper child-parent relationship",
                "MenuButtonChildParent",
                "FAIL",
                test_message,
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

