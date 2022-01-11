from time import sleep

from selenium import webdriver

from framework.element import Element
from framework.libs.test_pattern import SuperTest


framework_version = 0
WCAG = "2.4.3"
name = "Ensure that there are no elements with tabindex > 0"
depends = []
webdriver_restart_required = False
locator_required_elements = []
elements_type = ""
test_data = [
    {
        "page_info": {"url": r"focus/page_good_tabindex.html"},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"focus/page_bugs_tabindex.html"},
        "expected_status": "FAIL"
    },
]


def test(webdriver_instance: webdriver, activity, element_locator, dependencies=None):
    return TabindexTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class TabindexTest(SuperTest):

    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self._main()

    def _main(self):
        if self.driver.find_elements_by_xpath(".//body"):
            self.set_pass_status()
            sleep(30)  # TODO: remove before group testing
            all_bug_elements = self.driver.find_elements_by_xpath(".//*[@tabindex>'0']")
            if all_bug_elements:
                problem_elements = Element.from_webelement_list(all_bug_elements, self.driver)
                self.result["status"] = "FAIL"
                self.result["message"] = "There are elements with tabindex > 0"
                self.result["checked_elements"] = problem_elements
                for element in problem_elements:
                    self.result["elements"].append({
                        "element": element,
                        "problem": "The element have incorrect tabindex",
                        "severity": "FAIL"
                    })

