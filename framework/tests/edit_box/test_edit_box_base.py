from selenium import webdriver
from selenium.webdriver.support import expected_conditions

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.tests.edit_box.base_func import BaseFunc
from framework.element import ElementLostException

WCAG = "1.1.1"
framework_version = 4
webdriver_restart_required = False
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "edit_boxes/page_base_edit_box.html"
        },
        "expected_status": "PASS",
        "expected_additional_content_length": {
            "edit_boxes": 1
        }
    }
]


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """Test for search edit boxes"""
    activity.get(webdriver_instance)
    return EditBox(webdriver_instance, element_locator).result_dict()


class EditBox:

    def __init__(self, driver, locator):
        self._dr = driver
        self.locator = locator
        self.checked_elements = []

    @property
    def _func(self):
        return BaseFunc(self._dr)

    def result_dict(self):
        boxes = self.main()
        result = {"status": "PASS", "message": "", "edit_boxes": boxes, "checked_elements": self.checked_elements}
        if not boxes:
            result["status"] = "NOELEMENTS"
            result["message"] = "No elements like edit box"
        return result

    def _wrap(self, el):
        return ElementWrapper(el, self._dr)

    def main(self):
        """Found edit boxes"""
        boxes = []
        self.find_boxes_for_check()
        for el in self.checked_elements:
            if self.__clarification(el):
                if self._visible(el):
                    boxes.append({
                        "box": el,
                    })
        return boxes

    def _visible(self, el: Element):
        return expected_conditions.visibility_of(el.get_element(self._dr))(self._dr)
    
    def find_boxes_for_check(self):
        """
        Method for finding possible edit boxes
        """
        elements = self.locator.get_all_by_xpath(self._dr, "//body//*[not(ancestor::table)]")
        for el in elements:
            if self.__possible_boxes(el):
                self.checked_elements.append(el)

    def __clarification(self, el: Element):
        """

        """
        try:
            send = self._func.send_text(el)
        except ElementLostException:
            send = None
        exist_btn = self.existence_btn(el)
        parents = el.get_parent(self._dr)
        if parents:
            parents = parents.tag_name == "form"
        child_from = el.find_by_xpath("./*[child::form]", self._dr)
        attr_text = el.get_attribute(self._dr, "text")
        return any([send, exist_btn, parents, child_from, attr_text])

    def __possible_boxes(self, el):
        """
        Checks for possible edit box
        """
        by_keywords = self._func.contains_keywords(el)
        text_area = el.tag_name in ["textarea", "input"]
        select_btn = el.tag_name in ["select"]
        subm_btn = el.get_attribute(self._dr, "type") == 'submit'
        return any([by_keywords, text_area, select_btn, subm_btn])

    def existence_btn(self, element: Element):
        """
        Search a button next to an item
        """
        elements = element.find_by_xpath(".//*", self._dr)
        return any([el for el in elements if self._func.is_btn(el)])
