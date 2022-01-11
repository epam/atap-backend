from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.tests.edit_box.base_func import BaseFunc

name = "Ensures that found edit boxes was working"
WCAG = "1.3.1"
depends = ["test_edit_box_base"]
webdriver_restart_required = True
framework_version = 2
elements_type = "edit field"
test_data = [
    {
        "page_info": {
            "url": "edit_boxes/page_base_edit_box.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "edit_boxes/page_bugs_working.html"
        },
        "expected_status": "PASS",
        "expected_problem_count": 3
    }
]

KEYWORDS = {
    "disabled",
    "readonly"
}

# !RENAME ME
def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator, dependencies):
    """
    This test checks whether the edit box is functioning.
    Bottom line is, interactable edit boxes only, use for tests following. 
    """
    activity.get(webdriver_instance)
    return WorkingBoxes(webdriver_instance, element_locator, dependencies).result()


class WorkingBoxes:

    def __init__(self, driver, locator: ElementLocator, dependency):
        self._dr = driver
        self._dep = dependency
        self._locator = locator
        self.working = []

    @property
    def _func(self):
        return BaseFunc(self._dr)

    def result(self):
        result_dict = {
            "status": "PASS",
            "message": "",
            "elements": [],
            "checked_elements": [],
            "working": self.working
        }
        boxes = self._main()
        if boxes is None:
            result_dict["status"] = "NOELEMENTS"
            result_dict["message"] = "This page doesn't have edit boxes"
        elif boxes:
            # * base test <- result_dict["status"] = "FAIL"
            result_dict["elements"] = boxes
            result_dict["message"] = "Found some edit boxes that don't work"
        return result_dict

    def _main(self):
        bad_elements = []
        for elem in self._dep["test_edit_box_base"]['edit_boxes']:
            el = elem['box']
            if not el:
                return None
            if self.check_working(el):
                bad_elements.append(
                    {
                        "element": el,
                        "problem": "Non-functional edit box"
                    }
                )
            else:
                self.working.append({"box": el})
        return bad_elements

    def check_working(self, el):
        """
        Find out user can interact with text box
        Args: el (Element)
        Returns: bool: any of 3 conditions
        """
        return any([self._disabled(el),
                    not self.enable_after_click(el)])

    def _disabled(self, el):
        """
        Checks, if edit box disabled or readonly
        Args: el (Element)
        Returns: bool: if the el disabled
        """
        attributes = self._dr.execute_script("""
            var attrs = [];
            for (idx=0; idx < arguments[0].attributes.length; ++idx) {
                attrs[idx] = arguments[0].attributes[idx].name
                };
                return attrs;
            """, el.get_element(self._dr))
        return any([rule for rule in KEYWORDS if rule in attributes])

    def enable_after_click(self, el):
        """
        !!! PLUG
        Doesnt work as expected, though no much need
        Click on box area of el - check it will work.
        Click 0-2 lvls up
        Args: el (Element)
        Returns: bool: if click action turned el on
        """
        return True
        # el.click(self._dr)
        # limit = 0
        # el_one = el
        # while limit < 3:
        #     el_one.click(self._dr)
        #     if self._func.send_text(el):  # * not sure send_text works as it supposed to
        #         print('res True')
        #         return True
        #     limit += 1
        #     el_one = el_one.get_parent(self._dr)
        # print('res False')
        # return False
