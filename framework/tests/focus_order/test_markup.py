from selenium import webdriver

from framework.element import Element
from framework.libs.test_pattern import SuperTest

framework_version = 4
WCAG = "2.4.3"
name = "Ensures that order of top-level landmarks is correct"
depends = []
webdriver_restart_required = False
locator_required_elements = []
elements_type = ""
test_data = [
    {
        "page_info": {"url": r"focus/page_good_markup.html"},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"focus/page_bugs_markup.html"},
        "expected_status": "FAIL"
    },

]


def test(webdriver_instance: webdriver, activity, element_locator, dependencies=None):
    return MarkupTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class MarkupTest(SuperTest):

    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self._main()

    def _main(self):
        self.activity.get(self.driver)
        if self.driver.find_elements_by_xpath(".//body"):
            self.set_pass_status()
            all_elements = self.driver.find_elements_by_xpath(".//*")
            all_elements = Element.from_webelement_list(all_elements, self.driver)
            elements_order = dict()
            for index, element in enumerate(all_elements):
                elements_order[element.tag_name] = {"position": index, "element": element}

            header = self.get_value_if_exist(elements_order, "header")
            main = self.get_value_if_exist(elements_order, "main")
            footer = self.get_value_if_exist(elements_order, "footer")

            if footer and main and header:
                if main["position"] > footer["position"]:
                    self.result["status"] = "FAIL"
                    self.result["message"] = "There are elements with incorrect DOM position"
                    self.result["checked_elements"].extend([main["element"], footer["element"]])
                    self.result["elements"].append({
                        "element": footer["element"],
                        "problem": "The element have incorrect DOM position. Should be 'header' -> 'main' -> 'footer'",
                        "severity": "FAIL"
                    })
                if header["position"] > main["position"]:
                    self.result["status"] = "FAIL"
                    self.result["message"] = "There are elements with incorrect DOM position"
                    self.result["checked_elements"].extend([header["element"], main["element"]])
                    self.result["elements"].append({
                        "element": main["element"],
                        "problem": "The element have incorrect DOM position. Should be 'header' -> 'main' -> 'footer'",
                        "severity": "FAIL"
                    })

    @staticmethod
    def get_value_if_exist(dict_, key):
        try:
            value = dict_[key]
        except KeyError:
            value = None
        return value
