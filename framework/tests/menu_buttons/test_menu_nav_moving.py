from selenium import webdriver

from framework.element import Element
from framework.libs.test_pattern import NavigationTest

__all__ = []

framework_version = 4
WCAG = "2.1.1"
name = "Ensure that dropdown menu support keyboard navigation mechanism"
depends = ["test_dd_detector"]
webdriver_restart_required = False
elements_type = "menu"
test_data = [
    {
        "page_info": {"url": r"dropdowns/page_good_menu_button_1.html "},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"dropdowns/page_bugs_no_expand.html"},
        "expected_status": "FAIL"
    }
]
bug_message = "Some menu dropdowns have incorrect navigation mechanism"
element_problem_message = "A dropdown menu doesn't support keyboard navigation"


def test(webdriver_instance: webdriver, activity, element_locator, dependencies=None):
    return MenuNavMoving(webdriver_instance, activity, element_locator, dependencies).get_result()


class MenuNavMoving(NavigationTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.elements_to_check = self.dependency_data[depends[0]]["dependency"]
        if not self.elements_to_check:
            return
        self.set_pass_status()
        self._main()

    def _main(self):
        Element.safe_foreach(list(self.elements_to_check.keys()), self._navigation_check)

    def _navigation_check(self, button):
        data = self.elements_to_check[button]
        if data["type"] != "menu":
            return
        self.result["checked_elements"].append(button)

        if not data["kbd_activation"]:
            self.append_error_message(bug_message, button, element_problem_message, "MenuActivation")
        else:
            listholder = self.get_ul(data["dd_elements"])
            visible_elements = self.get_items(listholder)
            if not any(self.check_focus_moving(button, visible_elements, nav_key)
                       for nav_key in self.navigation_keys):
                self.append_error_message(bug_message, button, element_problem_message, "MenuNavigation")

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

    @staticmethod
    def get_ul(elements):
        for element in elements:
            if element.tag_name == "ul":
                return element

