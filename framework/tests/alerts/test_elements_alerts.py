from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from framework.element import ElementLostException
from selenium.webdriver.common.keys import Keys

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.tests.alerts.alert_meta import AlertsController

from itertools import dropwhile


name = "Ensures that after an error in the input field, an element with an error is identified,\
       and the error is described to the user in a text notification"
WCAG = "3.3.1"
depends = ["test_submit_alerts", "spacy_en_lg"]

framework_version = 4
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
            "url": "edit_boxes/page_bugs_alerts.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    },
    {
        "page_info": {
            "url": "alerts/page_good_alerts.html"
        },
        "expected_status": "PASS",
    },
    {
        "page_info": {
            "url": "alerts/page_bad_submit.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator, dependencies):
    """
    Test inspects input elements from edit_box_base dependency.
    Element PASS if only it was verified by one of 'missing*' criterion,
    so it should have text description itself or by some element from page changes and
    pass accessibility criterion, itself or by some element from page changes (e. g. heading with text).
    Page changes are new or modified web elements after form submition or after TAB key action.
    Possible errors include:
        * Invalid accessibility criterion
        * Invalid accessibility criterion and absence of text description
        * Full absence of alerts after submition
    """
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
            result_dict["status"] = "FAIL"
            result_dict["message"] = "This page doesn't have edit boxes: bug 3.3.1"
            result_dict["elements"] = [{"element": None,
            "problem": "No alerts found",
            "severity": "FAIL"}]
        elif boxes:
            result_dict["status"] = "FAIL"
            result_dict["elements"] = boxes
            result_dict["message"] = "There are problems with edit boxes: bugs 3.3.1, 1.4.1"
        else:
            result_dict["message"] = "All alerts work well."
        return result_dict
    
    def __main(self):
        bad_elements = []
        validators = [self.missing_role, self.missing_heading,
                        self.missing_aria, self.missing_alert, self.missing_hyperlink]
        # functionality disabled, as errors wanted instead of interaction
        # self.set_elem_actions()
        # receive good forms and elements changes from test_submit_alerts
        self._act.get(self._dr)
        forms = self._dep["test_submit_alerts"]["checked_elements"]
        forms_changes = self._dep["test_submit_alerts"]["form_changes"]
        box_elements = {form: self.edit_box_base(form) for form in forms}
        other_boxes, other_changes = self._out_of_form_edit_boxes()
        if not (forms or other_boxes):
            return None
        if forms:
            forms_failes = self._failes_after_submit(
            box_elements.values(), forms, forms_changes.values(), validators)
            bad_elements.extend(forms_failes)
        if other_boxes:
            other_boxes_failes = self._failes_in_form(other_boxes, other_changes, validators)
            unq_elems = {elem['element'].source for elem in bad_elements}
            for other_fail in other_boxes_failes:
                if other_fail['element'].source not in unq_elems:
                    bad_elements.append(other_fail)
        return bad_elements
    
    def _out_of_form_edit_boxes(self):
        self._act.get(self._dr)
        non_form_boxes = []
        page_changes = []
        non_form_xpath = f"//*[{' or '.join([f'self::{input}'for input in self.INPUTS])}]\
                                                                [not(ancestor::form)]"
        non_form_boxes = self._locator.get_all_by_xpath(self._dr, non_form_xpath)
        saved_elements = self.save_visible()
        self.BOXES_MESSAGE = dict()  # reset
        body_form = self._locator.get_all_by_xpath(self._dr, "//body")[0]
        non_form_boxes = self._selector_intersection(self.edit_box_base(body_form), non_form_boxes)
        non_form_boxes = self.filter_box_elems(non_form_boxes)
        if not non_form_boxes:
            return [], []
        submit = self.submit_form(body_form)
        if not submit:
            return [], []
        self.ALERT_TEXT = self.detected_alert()
        non_form_boxes = self.filter_box_elems(non_form_boxes)
        page_changes = self.get_changed_elements(saved_elements, non_form_boxes)
        if not (page_changes or self.ALERT_TEXT):
            return [], []
        return non_form_boxes, page_changes
    
    
    def _form_sent(self, form: Element, form_elements :list):
        """
        Method is called in 'for' cycle in '_failes_after_submit'
        It activate changes - provides submit of form
        """
        submit = False
        form_elements = self.filter_box_elems(form_elements)
        self.BOXES_MESSAGE = dict()
        self.BOXES_DESCRIBED = set()
        # self.complete_form(form_elements)
        submit = self.submit_form(form)
        self.ALERT_TEXT = self.detected_alert()
        return submit
    
    def _failes_in_form(self, form_elements: list, form_changes: list, validators : list):
        """
        Method is called in 'for' cycle in '_failes_after_submit' as
        previous method - '_form_sent' finished fine.
        Verifies all form changes are located and inspect form boxes on conditions,
        conditions are realised by validators functions, applied to changed elements.
        In cycle checks if some element do not fail at least one validator.
        """
        alibi = False
        for elem in self.filter_box_elems(form_elements):
            self.BOXES_MESSAGE[elem.get_selector()] = self.elem_vocab(elem, label=self.found_label(elem))
        self.CHANGED = form_changes
        for change in form_changes:
            alibi = list(dropwhile(lambda func: func(change), validators))  # WCAG tests on change until it pass  
            if alibi:
                pass  # alibi means change was useful
            if not self.BOXES_MESSAGE:
                break

        blame_innocent = True and form_changes
        if set(self.BOXES_MESSAGE.keys()).intersection(form_changes):
            blame_innocent = False
        problems = dict(with_text="Bad alert for element, it has text description: bug 3.3.1",
                    without_text="Bad alert for element: bug 3.3.1 and 1.4.1")
        error_id = dict(with_text="AlertFailHasText", without_text="AlertFail")
        form_changes = [change.source for change in form_changes]
        failes = [{
            "element": Element(self._dr.find_element_by_css_selector(box), self._dr),
            "problem": f"{problems['with_text'] if box in self.BOXES_DESCRIBED else problems['without_text']}",
            "error_id": f"{error_id['with_text'] if box in self.BOXES_DESCRIBED else error_id['without_text']}",
            "severity": "FAIL"
            }
            for box in self.BOXES_MESSAGE.keys() if box in form_changes or blame_innocent]
        
        return failes

    def _failes_after_submit(self, box_elements: list, forms: list, form_changes: list, validators : list):
        """
        Method takes previous submition results from elements with <form> parent or outer edit_boxes
        For found form elements calls '_form_sent' and '_failes_in_form' methods,
        Accumalates all errors
        returns total failes on webpage or None when no changes appeared  
        """
        failes = []
        self._act.get(self._dr)
        for form, elements, changes in zip(forms, box_elements, form_changes):
            submit = self._form_sent(form, elements)
            if not submit:
                raise NameError('Did not submit valid form, please retry test')
            form_failes = self._failes_in_form(elements, changes, validators)
            failes.extend(form_failes)
        return failes
