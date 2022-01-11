from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException, TimeoutException
from selenium.webdriver.common.keys import Keys

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.tests.alerts.alert_meta import AlertsController


name = "Ensures that notifications about errors will appear after\
        sending TAB key through the input field element"
WCAG = "3.3.1, 4.1.3"
depends = ["test_submit_alerts", "spacy_en_lg"]

framework_version = 0
elements_type = "edit field"
test_data = [
    {
        "page_info": {
            "url": "alerts/page_good_alerts.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "alerts/page_bad_tab_inputs.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    },
]


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    return AlertsBox(webdriver_instance, activity, element_locator, dependencies).result()


class AlertsBox(AlertsController):
    def __init__(self, driver, activity, locator, dependencies):
        super().__init__(driver, activity, locator, dependencies)
        self._dep = dependencies

    def result(self):
        result_dict = {
            "status": "PASS",
            "message": "",
            "elements": [],
            "checked_elements": [],
        }
        boxes = self.__main()
        if boxes is None:
            result_dict["status"] = "NOELEMENTS"
            result_dict["message"] = "This page doesn't have edit boxes."
        elif boxes:
            result_dict["status"] = "FAIL"
            result_dict["elements"] = boxes
            result_dict["message"] = "Problems with edit boxes after sending TAB key."
        else:
            result_dict["message"] = "All input validation (TAB) alerts work well."
        result_dict["checked_elements"] = []
        return result_dict

    def __main(self):
        bad_elements = []
        self._act.get(self._dr)
        forms = self._dep["test_submit_alerts"]["checked_elements"]
        box_elements = {form: self.edit_box_base(form) for form in forms}
        body_form, external_boxes = self._external_edit_boxes()
        box_elements.update({body_form: external_boxes})
        if not box_elements:
            return None
        boxes = box_elements.copy()
        box_elements = set()
        for box_group in boxes.values():
            for box in box_group:
                box_elements.add(box)
        for box in box_elements:
            tab_fail = self._check_after_tab(box)
            bad_elements.append(tab_fail)
        bad_elements = list(filter(None, bad_elements))
        return bad_elements

    def _check_after_tab(self, edit_box: Element):
        
        """
        Method is used for catching errors after sending TAB key to edit_box.
        Collects changes after key sent, then invokes validator - _tab_changes_fine method.
        If there changes and then validator returned False, returns an issue of edit_box.
        """
        try:
            self._act.get(self._dr)
        except TimeoutException:
            pass
        self.BOXES_MESSAGE = {}
        self.ALERT_TEXT = set()
        self.BOXES_MESSAGE[edit_box] = self.elem_vocab(edit_box, label=self.found_label(edit_box))
        saved_elements = self.save_visible()
        saved_elements.update({self.source(edit_box): edit_box})
        try:
            edit_box.get_element(self._dr).send_keys(Keys.TAB)
            self.detected_alert()
        except ElementNotInteractableException:
            return None
        try:
            edit_box.get_element(self._dr)
            page_changes = self.get_changed_elements(saved_elements, [edit_box])
        except (ElementLostException, StaleElementReferenceException):
            page_changes = self.get_changed_elements(saved_elements, [])
        if not (page_changes or self.ALERT_TEXT):
            return None
        problem = "Bad alert for element after sendind TAB: bug 3.3.1, 4.1.3"
        error_id = "EditBoxTabAlert"
        if not self._tab_changes_fine(edit_box, page_changes):
            return {
            "element": edit_box,
            "problem": problem,
            "error_id": error_id,
            "severity": "FAIL"
            }

    def _tab_changes_fine(self, edit_box: Element, tab_changes: list):
        """
        Method gets tab_changes, filters them on text intersection condition.
        Then if any changes remained, method checks there are necessary aria attributes.
        If any of attributes found for edit_box, returns True. 
        """
        # first of all check textual correspondance
        vocabs = {elem: self.elem_vocab(elem, label=self.found_label(elem))
                                                    for elem in tab_changes}
        for change in tab_changes.copy():
            elem_vocab = vocabs[change] 
            text_flag = set(filter(lambda word: word in self.BOXES_MESSAGE[edit_box], elem_vocab))
            # WARN case?
            if not text_flag:
                text_flag = set(filter(lambda word: word in self.COMMON_MESSAGE, elem_vocab))
            if not text_flag:
                tab_changes.remove(change)
        tab_changes = set(tab_changes)
        # check html attributes
        role_alert = {elem for elem in tab_changes
                        if elem.get_attribute(self._dr, 'role') == "alert"}
        tab_changes -= role_alert
        aria_polite = {elem for elem in tab_changes
                        if elem.get_attribute(self._dr, 'aria-live') == "polite"}
        aria_described = []
        if edit_box.tag_name == "input":
            aria_attr = edit_box.get_attribute(self._dr, 'aria-describedby')
            if aria_attr:
                described_xpath = f"//*[@id='{aria_attr}' or @name='{aria_attr}']"
                aria_described = self._locator.get_all_by_xpath(self._dr, described_xpath)
        # could be different polite and describedby? - suppose not
        if not aria_described:
            aria_polite = set()
        if any([role_alert, aria_polite]):
            return True
        return False    

    def _external_edit_boxes(self):
        """
        Simply collect elements like edit boxes from DOM outside of <form> 
        :return: body element, edit boxes from body and outside of forms
        """
        non_form_boxes = []
        page_changes = []
        non_form_xpath = f"//*[{' or '.join([f'self::{input}'for input in self.INPUTS])}][not(ancestor::form)]"
        non_form_boxes = self._locator.get_all_by_xpath(self._dr, non_form_xpath)
        body_form = self._locator.get_all_by_xpath(self._dr, "//body")[0]
        non_form_boxes = set(self.edit_box_base(body_form)).intersection(non_form_boxes)
        non_form_boxes = self.filter_box_elems(non_form_boxes)
        return body_form, non_form_boxes
