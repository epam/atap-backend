from framework.element import Element
from framework.libs.test_pattern import SuperTest


framework_version = 4
WCAG = "4.1.2, 2.1.1"
name = "Ensure that checkboxes have appropriate role"
depends = ["test_checkbox_base"]
webdriver_restart_required = True
elements_type = "checkbox"
test_data = [
    {
        "page_info": {
            "url": r"checkbox/page_good_checkbox.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": r"checkbox/page_bugs_checkbox.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    },
#     # {
#     #     "page_info": {
#     #         "url": r"checkbox/pretty_checkbox.html"
#     #     },
#     #     "expected_status": "PASS",
#     # }, # quite heavy
]
test_message = """Some checkboxes have incorrect role and/or tabindex: bug 4.1.2, 2.1.1"""


def test(webdriver_instance, activity, element_locator, dependencies):
    """
    Test on accessibility of elements that behave like checkboxes. 
    """
    return CheckboxTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class CheckboxTest(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.framework_element = None
        self.checkboxes = self.dependency_data[depends[0]]["dependency"].copy()
        self._main()

    def _main(self):
        if not self.checkboxes:
            self.result["status"] = "NOELEMENTS"
            self.result["message"] = "No chechbox elements"
            self.result["elements"] = []
        else:
            self.set_pass_status()
            self.result["checked_elements"] = list(self.checkboxes.keys())
            Element.safe_foreach(self.result["checked_elements"], self._role_check)

    def _role_check(self, element: Element):
        """
        Checks web element for checkbox criteria.
        If element behaves as checkbox and don't pass criteria,
        error will be appended to the test result.
        """
        # if element pass or one of it's valuable childs:
        certified_role, certified_index = False, False
        for elem in self.checkboxes[element]:
            role = self.get_attribute(elem, "role")
            _type = self.get_attribute(elem, "type")
            if _type == "checkbox":
                return
            if role == "checkbox":
                certified_role = True
                if self.get_attribute(elem, "tabindex") == "0":
                    certified_index = True
                    break
        if not certified_index:
            if not certified_role:
                self.report_issue(
                    element,
                    "An element with checkbox behavior doesn't have appropriate role: bug 4.1.2",
                    "CheckboxRole",
                    "FAIL",
                    test_message)
                return
            self.report_issue(
                element,
                "The element have incorrect tabindex: bug 2.1.1",
                "CheckboxTabindex",
                "FAIL",
                test_message)
