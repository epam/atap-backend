""" Test ensures that buttons have appropriate roles (WCAG 4.1.2)

"""
from framework.libs.test_pattern import SuperTest
from framework.element import Element



__all__ = []

framework_version = 4
WCAG = "4.1.2"
name = "Ensures that buttons are implemented correctly with all applicable attributes and are operable using keyboard (2.1.1, 4.1.2)"
BUTTON_ROLES = ("button", "checkbox", "switch", "menu", "radio")
depends = ["test_buttons_purpose"]
webdriver_restart_required = False
elements_type = "button"
test_data = [
    {
        "page_info": {
            "url": r"page_good_buttons.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_bugs_buttons.html"
        },
        "expected_status": "FAIL"
    }
]
test_message = "Some buttons have incorrect role and/or doesn't able to receive focus using keyboard"


def test(webdriver_instance, activity, element_locator, dependencies):
    return ButtonsRole(webdriver_instance, activity, element_locator, dependencies).get_result()


class ButtonsRole(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.buttons = self.dependency_data[depends[0]]["dependency"]
        if self.buttons:
            self.set_pass_status()
        self._main()

    def _main(self):
        Element.safe_foreach(self.buttons, self._check)

    def _check(self, element: Element):
        self.result["checked_elements"].append(element)
        # print()
        # print("_"*80)
        if element.tag_name in ("button", "select") or (element.tag_name == "input" and
                                            self.get_attribute(element, "type") in ("button", "reset", "submit")):
            return
        role = self.get_attribute(element, "role")
        if role not in BUTTON_ROLES and element.tag_name != "a":
            # WCAG 1.3.1 4.1.2
            # print("ButtonRole")
            # print(element.source[:240:], '\n')
            severity = "WARN" if element.tag_name == "div" else "FAIL"
            self.report_issue(
                element=element,
                problem_message="An element with button behavior don't have appropriate role",
                error_id="ButtonRole",
                test_message=test_message,
                severity=severity,
            )
        if element.tag_name == "a" and ('href="#' in element.source or 'href="?' in element.source)\
                and self.get_attribute(element, "role") != "button":
            # WCAG 1.3.1 4.1.2
            # print("ButtonImplement")
            # print(element.source[:240:], '\n')
            self.report_issue(
                element=element,
                problem_message="An element that act as button are not implemented as button",
                error_id="ButtonImplement",
                test_message=test_message,
                severity="WARN",
            )

        if element.tag_name not in ('button', 'a', 'input', 'select') and self.get_attribute(element, "tabindex") != "0":
            # WCAG 2.1.1
            # print("ButtonTabindex", '\n')
            # print(element.source[:240:])
            self.report_issue(
                element=element,
                problem_message="The element have incorrect tabindex",
                error_id="ButtonTabindex",
                severity="FAIL",
                test_message=test_message,
            )
