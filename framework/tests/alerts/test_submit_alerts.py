from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.tests.alerts.alert_meta import AlertsController


name = "Ensures that page has forms that can be submitted and\
        errors will appear after submit action"
WCAG = "3.3.1"

framework_version = 4
depends = ["spacy_en_lg"]
elements_type = "form"
test_data = [
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
    },
    {
        "page_info": {
            "url": "edit_boxes/page_bugs_alerts.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    return SubmitAlerts(webdriver_instance, activity, element_locator, dependencies).result()


class SubmitAlerts(AlertsController):
    def __init__(self, driver, activity, locator, dependencies):
        super().__init__(driver, activity, locator, dependencies)
    
    def result(self):
        result_dict = {
            "status": "PASS",
            "message": "",
            "elements": [],
            "checked_elements": [],
            "form_changes": []
        }
        fails, forms, changes = self.__main()
        if forms is None:
            result_dict["status"] = "FAIL"
            result_dict["message"] = "This page doesn't have <form> elements"
            result_dict["elements"] = [{"element": None,
            "problem": "No forms found",
            "severity": "FAIL"}]
            result_dict["checked_elements"] = []
            result_dict["form_changes"] = []
            return result_dict
        if fails:
            result_dict["status"] = "FAIL"
            result_dict["elements"] = fails
            result_dict["message"] = "There are wrong forms on page"
        else:
            result_dict["message"] = "All <form> elements are reliable"
        result_dict["checked_elements"] = forms
        result_dict["form_changes"] = changes

        return result_dict

    @classmethod
    def _error_message(cls, element, message):
        msg_to_err = dict(
            visibility={"problem": "<form> is not visible",
                "severity": "WARN", "error_id": "formIsNotVisible"},
            submit={"problem": "<form> has no submit",
                "severity": "FAIL", "error_id": "formHasNoSubmit"},
            redirect={"problem": "url changes after submit",
                "severity": "WARN", "error_id": "urlChangesAfterSubmit"},
            changes={"problem": "nothing changed after <form> submit",
                "severity": "FAIL", "error_id": "noChangesAfterSubmit"})
        error = {"element": element}
        error.update(msg_to_err[message])
        return error

    def __main(self):
        """
        Validate if we can submit from the form.
        If submit succeded, validate if there are changes on page,
        so there may be alerts after submit action.
        """
        self.ALERT_TEXT = set()  # data mixes when running unittest, leads to fail
        fail_elements = []
        url = self._dr.current_url
        # self.set_elem_actions()  # turned off elem interaction
        elements = self.save_visible()
        forms = self._locator.get_all_by_xpath(self._dr, "//body//form")
        if not forms:
            return None, None, None
        checked_elements = []
        form_changes = dict()
        for form in forms:
            bad_form, message, changed = self.test_form_fail(form, forms, url, elements)
            if bad_form:
                error = self._error_message(form, message)
                fail_elements.append(error)
            else:  # cant remove bad_form - removes it from forms
                checked_elements.append(form)
                form_changes[form] = changed
        return fail_elements, checked_elements, form_changes

    def test_form_fail(self, form: Element, forms: list, url: str, saved_elements: dict):
        bad_form, message, page_changes = form, None, set()
        if not self.visible(form):
            message = "visibility" 
            return bad_form, message, set()
        form_elements = [elem for elem in form.find_by_xpath('.//*', self._dr)
                                if elem.tag_name in self.INPUTS]
        form_elements = self.filter_box_elems(form_elements)
        saved_elements.update({self.source(elem): elem for elem in form_elements})
        # self.complete_form(form_elements)  # turned off elem interaction
        submit = self.submit_form(form)
        self.detected_alert()
        if not submit:
            message = "submit"
            return bad_form, message, set()
        if self.redirection(url, forms):
            message = "redirect"
            return bad_form, message, set()
        form_elements = self.filter_lost_elements(form_elements)
        page_changes = self.get_changed_elements(saved_elements, form_elements)
        self.CHANGED = page_changes
        if not (page_changes or self.ALERT_TEXT):
            message = "changes"
            return bad_form, message, set()
        bad_form = None
        return bad_form, message, page_changes
