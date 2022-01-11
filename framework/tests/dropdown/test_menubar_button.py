""" All test_menubar_* test files was added for future menubar feature but was not released at creating phase"""

from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.test_pattern import SuperTest

__all__ = []

framework_version = 0
WCAG = "4.1.2"
name = "Ensure that menubar buttons have correct role"
depends = ["test_dropdown_detector"]
webdriver_restart_required = False
elements_type = "menubar"
test_data = [  # TODO Unit test

    {
        "page_info": {"url": r""},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r""},
        "expected_status": "FAIL"
    },
]


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return MenubarButtonRole(webdriver_instance, activity, element_locator, dependencies, debug).main().get_result()


class MenubarButtonRole(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.elements_to_check = self.dependency_data[depends[0]]["dependency"]["menubars"]
        if self.elements_to_check:
            self.set_pass_status()

    def main(self):
        self.activity.get(self.driver)
        Element.safe_foreach(self.elements_to_check, self._role_check)

    def _role_check(self, data):
        """

        :param data: A tuple with element (button), visible after activation
        elements and method by which button was activated.
        :return:
        """
        button, elements, activation_method = data

        self.result["checked_elements"].append(button)
        if button.get_element(self.driver).get_attribute("role") != "menuitem":
            self.result["status"] = "FAIL"
            self.result["message"] = ""  # TODO
            self.result["elements"].append({
                "element": button,
                "problem": "",  # TODO
            })
