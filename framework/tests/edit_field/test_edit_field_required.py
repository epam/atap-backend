from framework.element import Element
from framework.libs.test_pattern import SuperTest

# from framework.libs.test_pattern import wrap_test_output

framework_version = 4
name = "Ensures that edit fields which are required to fill have appropriate attributes"
locator_required_elements = []
depends = ["test_edit_field_name"]
webdriver_restart_required = False
WCAG = "4.1.2"
elements_type = "edit field"
test_data = [
    {
        "page_info": {
            "url": r"edit_fields/page_good_edit_fields_required.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "edit_fields/page_bugs_edit_fields_required.html"
        },
        "expected_status": "FAIL"
    },
]
test_message = "Some edit fields doesn't notify that they are required"

KEY_WORDS = ["*", "required", "must be", "field is", "fill", "enter"]
ERROR_KEYWORDS = ('error',)
TOOLBAR_END = 120


# @wrap_test_output
def test(webdriver_instance, activity, element_locator, dependencies):
    return Test(webdriver_instance, activity, element_locator, dependencies).get_result()


class Test(SuperTest):
    def __init__(self, webdriver_instance, activity, element_locator, dependencies):
        super(Test, self).__init__(webdriver_instance, activity, element_locator, dependencies)
        self.data = dependencies["test_edit_field_name"]["active_fields"]
        self.elements_data = {}
        self.submit_buttons = []
        self.other_buttons = []
        self.main()

    def main(self):
        if not self.data:
            return
        self.set_pass_status()
        Element.safe_foreach(self.data, self.collect_element_data)
        self.get_form_button()
        self.analyze_form_warnings()
        Element.safe_foreach(list(self.elements_data.keys()), self.check_required)

    def check_required(self, element):
        """

        :param element:
        :return:
        """
        data = self.elements_data[element]
        self.result["checked_elements"].append(element)

        # 1.
        if not data["is_labeled_as_required"] and (data["have_required_attribute"] or data["detected_as_required"]):
            # report FAIL 3.3.2 + 4.1.2
            # print('NoRequiredDescription')
            self.report_issue(
                element=element,
                problem_message="The edit field seems to be not marked as required.",
                error_id="NoRequiredDescription",
                severity="WARN",
                test_message=test_message,
            )

        # 2.
        if data["visible_text"].find("*") != -1 and data["have_required_attribute"] and \
                not data["form_have_required_description"]:  # and not data["in_a_form"]:
            # report WARN BP + 3.3.2
            # print(data["visible_text"])
            # print('NoDescriptionForAsterisk')
            self.report_issue(
                element=element,
                problem_message="Best Practise violation. The field should have properly description",
                error_id="NoDescriptionForAsterisk",
                severity="WARN",
                test_message=test_message,
            )

        # 3.
        if data["visible_text"].find("*") >= 0 and not data["have_required_attribute"]:
            # report BUG 3.3.3 + 4.1.2
            # print('NoRequiredAttr')
            self.report_issue(
                element=element,
                problem_message="The edit field don't have \"required\" or \"aria-required\" attribute",
                error_id="NoRequiredAttr",
                severity="FAIL",
                test_message=test_message,
            )

        # 4.
        if data["visible_text"].find("required") != -1 and not data["have_required_attribute"]:
            # report WARN BP + 4.1.2
            # print('BPNoRequiredAttrForCorrectCase')
            self.report_issue(
                element=element,
                problem_message="Best Practise violation. The field should have \"required\" or "
                                "\"aria-required\" attribute",
                error_id="BPNoRequiredAttrForCorrectCase",
                severity="WARN",
                test_message=test_message,
            )

        # 5.
        if data["in_a_form"] and data["form_have_required_description"] and data["visible_text"].find("*") != -1 and \
                not data["have_required_attribute"]:
            # report WARN BP
            # print('BPNoRequiredAttrForForm')
            self.report_issue(
                element=element,
                problem_message="Best Practise violation. The field should have \"required\" or "
                                "\"aria-required\" attribute",
                error_id="BPNoRequiredAttrForForm",
                severity="WARN",
                test_message=test_message,
            )

        # 6.
        if data["visible_text"] == "" and data["have_required_attribute"]:
            # report FAIL 1.3.1
            # print('MissedVisibleLabel')
            self.report_issue(
                element=element,
                problem_message='The edit field have the "required" or \"aria-required\" '
                                'attribute but don\'t have visible description',
                error_id="MissedVisibleLabel",
                severity="FAIL",
                test_message=test_message,
            )

        # 7.
        if data["is_labeled_as_required"] and data["have_required_aria-label_description"]:
            # report FAIL BP + 4.1.2
            # print('DuplicatedDescription')
            self.report_issue(
                element=element,
                problem_message="The edit field have excess aria-label value",
                error_id="DuplicatedDescription",
                severity="FAIL",
                test_message=test_message,
            )

    def is_required_by_attribute(self, element):
        element = element.get_element(self.driver)
        if element.get_attribute("required") or element.get_attribute("required") == "" or \
                element.get_attribute("aria-required") == "true":
            return True
        return False

    @staticmethod
    def is_required_by_label(text):
        for word in KEY_WORDS:
            if text.find(word) != -1:
                return True
        return False

    def collect_element_data(self, data):
        field, visible_text = data
        field_data = {
            "have_required_attribute": self.is_required_by_attribute(field),
            "visible_text": visible_text,
            "is_labeled_as_required": self.is_required_by_label(visible_text),
            "have_required_aria-label_description": self.is_required_by_aria_label(field),
            "in_a_form": self.is_in_a_form(field),
            "detected_as_required": False,
        }
        if field_data["in_a_form"]:
            field_data["form_have_required_description"] = self.check_form_description(field)
        else:
            field_data["form_have_required_description"] = False
        self.elements_data.update({field: field_data})

    def is_required_by_aria_label(self, element: Element):
        element = element.get_element(self.driver)
        aria_text = element.get_attribute("aria-label")
        if aria_text is None:
            return False
        if aria_text.find("*") != -1 or aria_text.find("required") != -1:
            return True
        return False

    def is_in_a_form(self, element):
        if element.find_by_xpath("ancestor::form", self.driver):
            return True
        else:
            return False

    def check_form_description(self, element):
        form_element = element.find_by_xpath("ancestor::form", self.driver)[0]
        previous_element = self.get_previous_dom_element(form_element)
        if previous_element and previous_element.tag_name == "p":
            text = previous_element.get_text(self.driver).lower()
            if text.find("required") != -1 and text.find("*") != -1:
                return True
        parent = element.get_parent(self.driver)
        preceding_elements = parent.find_by_xpath('preceding::*', self.driver)
        text = ""
        for elem in preceding_elements:
            text += elem.get_text(self.driver).lower()
        if text.find("required") != -1 and text.find("*") != -1:
            return True
        return False

    def get_previous_dom_element(self, element):
        parent = element.find_by_xpath("parent::*", self.driver)[0]
        parent_childs = parent.find_by_xpath("child::*", self.driver)
        for index, child in enumerate(parent_childs):
            if child == element:
                try:
                    return parent_childs[index-1]
                except IndexError:
                    return None

    def analyze_form_warnings(self):
        if self.submit_buttons:
            for button in self.submit_buttons:
                button.click()
                Element.safe_foreach(list(self.elements_data.keys()), self.update_fields_text)

    def update_fields_text(self, element):
        parent = element.get_parent(self.driver)
        parent_HTML = self.get_attribute(parent, "outerHTML").lower()
        for keyword in ERROR_KEYWORDS:
            if keyword in parent_HTML:
                self.elements_data[element]['detected_as_required'] = True
                break

    def get_form_button(self):
        submit_buttons = self.locator.get_all_by_xpath(self.driver, "//input[@type='submit']")
        self.submit_buttons = [x for x in submit_buttons if self.get_rect(x)['y'] > TOOLBAR_END]
        self.other_buttons = self.locator.get_all_by_xpath(self.driver, "//button|//input[@type='button']")
