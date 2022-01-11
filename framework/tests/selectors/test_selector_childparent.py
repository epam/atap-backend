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
elements_type = "selector"
test_data = [
    {
        "page_info": {"url": r"dropdowns/page_good_selector.html"},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"dropdowns/page_bugs_selector_listholder_role.html"},
        "expected_status": "FAIL"
    },
]

test_message = "Some sectors have incorrect child-parent realisation"
CORRECT_ACTION_MENU_ROLES = [
    'menuitem',
    'menuitemcheckbox',
    'menuitemradio'
]


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return SelectorChildParent(webdriver_instance, activity, element_locator, dependencies).get_result()


class SelectorChildParent(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        if not self.dependency_data[depends[0]]["dependency"]:
            return
        else:
            self.set_pass_status()
        self.dropdowns = self.dependency_data[depends[0]]["dependency"]
        self._main()

    def _main(self):
        for element in self.dropdowns.keys():
            if self.dropdowns[element]["type"] == "action":
                self._check_action_menu(element)
            elif self.dropdowns[element]["type"] == "listbox":
                self._check_listbox(element)
            elif element.tag_name == "select":
                self.result["checked_elements"].append(element)

    def _check_listbox(self, element: Element):
        self.result["checked_elements"].append(element)
        data = self.dropdowns[element]
        ul = self.get_ul(data["dd_elements"])
        li = self.get_li(data["dd_elements"])
        if self.get_attribute(ul, "role") != "listbox" or \
                any(map(lambda x: self.get_attribute(x, "role") != 'option', li)):
            self.report_issue(
                element=element,
                problem_message="Selector does not have proper child-parent relationship",
                error_id="SelectorChildParent",
                severity="FAIL",
                test_message=test_message,
            )

    def _check_action_menu(self, element: Element):
        self.result["checked_elements"].append(element)
        data = self.dropdowns[element]
        ul = self.get_ul(data["dd_elements"])
        li = self.get_li(data["dd_elements"])
        if self.get_attribute(ul, "role") != "menu" or \
                any(map(lambda x: self.get_attribute(x, "role") not in CORRECT_ACTION_MENU_ROLES, li)):
            self.report_issue(
                element=element,
                problem_message="Selector does not have proper child-parent relationship",
                error_id="SelectorChildParent",
                severity="FAIL",
                test_message=test_message,
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
