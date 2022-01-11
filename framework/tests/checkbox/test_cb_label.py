from selenium.webdriver.support.expected_conditions import visibility_of

from framework.element import Element
from framework.element_wrapper import ElementWrapper
from framework.libs.test_pattern import SuperTest
from framework.js_conductor import CompoundJavascriptEngager, eval_js
from .checkbox_scripts import execute_on_promise_script, jquery_check_script, illegal_label_script

import re


framework_version = 4  # TODO 5
WCAG = "1.3.1"
name = "Ensures that checkboxes have programmatic or text labels (1.3.1, 3.3.2, 4.1.2)"
depends = ["test_checkbox_base"]
webdriver_restart_required = True
elements_type = "checkbox"
test_data = [
    {"page_info": {"url": r"checkbox/page_good_checkbox.html"}, "expected_status": "PASS"},
    {
        "page_info": {"url": r"checkbox/page_bugs_checkbox.html"},
        "expected_status": "FAIL",
        "expected_problem_count": 3,
    },
    # {
    #     "page_info": {
    #         "url": r"checkbox/pretty_checkbox.html"
    #     },
    #     "expected_status": "FAIL",
    #     "expected_problem_count": 7
    # }  # quite heavy
]
test_message = "Some checkboxes don't have label or labels can't be identified by NVDA"


def test(webdriver_instance, activity, element_locator, dependencies):
    """
    Test on accessibility of labels of checkboxes like elements.
    Ensures checkboxes have appropriate labels.
    """
    return CheckboxTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class CheckboxTest(SuperTest, CompoundJavascriptEngager):
    def __init__(self, webdriver_instance, activity, locator, dependencies, timeout=4):
        self.framework_element = None
        self.dependency_data = dependencies
        scripts = [execute_on_promise_script, jquery_check_script, illegal_label_script]
        script_names = ["onPromise", "jQuery", "textLabels"]
        super().__init__(
            webdriver_instance,
            activity,
            locator,
            dependencies,
            scripts=scripts,
            script_names=script_names,
            timeout=timeout,
        )
        self.checkboxes = self.dependency_data[depends[0]]["dependency"].copy()
        self.label_elements = []
        self.labels_descendants = set()
        self.text_labels = []
        self.issue_elements = set()
        self._main()

    def _main(self):
        self.activity.get(self.driver)
        print("\ncheckboxes are", self.checkboxes)
        # handle special case
        if not self.checkboxes:
            self.result["status"] = "NOELEMENTS"
            self.result["message"] = "No chechboxes"
            self.result["elements"] = []
        else:
            # main case
            self.set_pass_status()
            self.issues = []
            self.result["checked_elements"] = list(self.checkboxes.keys())
            # collected checkboxes data
            self.label_elements = self.locator.get_all_by_xpath(
                self.driver, "//*[self::label or self::span][@for or @id or @name]"
            )
            print("\nlabel_elements", self.label_elements)
            self._find_labels_descendants()
            # collected programmatic labels
            print("\nlabels_descendants", self.labels_descendants)
            print("\nchecked_elements", list(self.checkboxes.keys()))
            # register javascript
            self.register_js(self.register_script, self.onpage_scripts)
            eval_js(
                "onPromise",
                "jQuery",
                recorder=self.fetch_script_source,
                evaluator=self.execute_script_eval,
                eval_confirm_async=map(
                    self.driver.execute_async_script,
                    [
                        """window.Timeout(arguments[0],
                    `window.withJQuery()`, `jQuery(document.body)`, 50);"""
                    ],
                ),
            )
            eval_js(
                "textLabels",
                recorder=self.fetch_script_source,
                evaluator=self.execute_script_eval,
            )

            # checkboxes localized as buttons without text, inputs prioritized
            corrected_checkboxes = self.driver.execute_script(
                """
                return window.correctedCheckboxes(arguments[0]);
            """,
                [
                    [*map(lambda elem: self.update_elem(elem, prop="element"), boxes)]
                    for boxes in self.checkboxes.values()
                ],
            )

            for i, box in enumerate(self.checkboxes.values()):
                if not corrected_checkboxes[i]:
                    corrected_checkboxes[i] = self.update_elem(box[-1], prop="element")

            print("\ncorrected_checkboxes", [Element(el, self.driver) for el in corrected_checkboxes])
            # get text labels (non-programmatic)
            self.text_labels = self.driver.execute_script(
                """
                return window.getCheckboxLabel(arguments[0]);
            """,
                corrected_checkboxes,
            )
            print(
                "\ntext labels",
                list(map(lambda el: None if not el else Element(el, self.driver), self.text_labels)),
            )
            # check criteria and report bugs
            Element.safe_foreach(
                list(zip(self.result["checked_elements"], self.text_labels)), self._label_bound_check
            )
            # place text nodes back to document instead of tmp created span element wrappers
            self.driver.execute_script("window.rollbackSpanTexts();")

            for issue, message, error_id in self.issues:
                issue = Element(issue, self.driver)
                if self._has_link(issue):
                    continue
                self.report_issue(
                    issue,
                    message,
                    error_id,
                    "FAIL",
                    test_message,
                )
            print("********************************\tRESULT\t********************************\n", self.result)

    # FIXME unexpected behavior for base returned checkboxes: https://contactform7.com/checkboxes-radio-buttons-and-menus/
    def _has_link(self, bug):
        for desc in bug.find_by_xpath("./descendant::*", self.driver) + [bug]:
            if desc.tag_name == "a":
                href = self.get_attribute(desc, "href")
                if href and re.match(r"^\w+|\/\w+", href):
                    return True
        return False

    def _label_bound_check(self, element_label: tuple):
        """
            Find out if checkbox has label that passes any of criteria below
        Args:
            element_label (tuple): pair of: Element instance - checkbox
            and text label for it, if present
        """
        print("********************************")
        print("_label_bound_check")
        fail_message = "The element has no label: bug 3.3.2, 4.1.2"
        error_id = "CheckboxLabelLost"
        element, text_label = element_label
        print("\ncheckboxes[element] FOR", element)
        # * must already be in base!
        input_elem = element.find_by_xpath("./input[@type='checkbox']", self.driver)
        if input_elem:
            input_elem = input_elem[0]
            self.checkboxes[element].append(input_elem) if not input_elem in self.checkboxes[element] else 1
        # *
        print("FOR elem in", self.checkboxes[element])
        for elem in self.checkboxes[element]:
            if elem.tag_name == "label":
                print("\nlabel elem")
                if "input" in self.get_attribute(elem, "outerHTML"):
                    print("label input")
                    return
            if elem.tag_name == "input" and self.get_attribute(elem, "type") == "checkbox":
                print("\ninput checkbox")
                if elem.get_selector() in self.labels_descendants:
                    print("in labels_descendants")
                    return
                if self._bound_label(elem, bound_by="for") or self._bound_label(elem, bound_by="id"):
                    print('bound_by="for"')
                    return
            elif self.get_attribute(elem, "role") == "checkbox":
                print("\nrole checkbox")
                if elem.get_text(self.driver):
                    print("text")
                    return
                if self.get_attribute(elem, "aria-label"):
                    print("aria-label")
                    return
                if self._bound_label(elem, bound_by="id") or self._bound_label(elem, bound_by="for"):
                    print("labelled-by")
                    return
            print("\ntext_label", Element(text_label, self.driver)) if text_label else 1
            if text_label:
                fail_message = "The element has incorrect label: bug 1.3.1, 4.1.2"
                error_id = "CheckboxLabelOff"
        print("\nbefore final report")
        print("element", element)
        element = input_elem or element
        print("\nelement input?", element.tag_name == "input")
        issue_elem = self.update_elem(element, prop="element")
        if not issue_elem in self.issue_elements:
            self.issues.append((issue_elem, fail_message, error_id))
            self.issue_elements.add(issue_elem)

    def _bound_label(self, elem: Element, bound_by):
        """
        This method looks up label with
        that is bound to elem, with for or aria-label or labelled by
        Returns:
            True if found label for elem, None if elem has no id
        """
        id_attr = (
            str(self.get_attribute(elem, "id"))
            + str(self.get_attribute(elem, "name"))
            + str(self.get_attribute(elem, "aria-labelledby"))
        )
        if not any(id_attr.split("None")):
            return None

        labels = self.label_elements
        for label in labels:
            if not visibility_of(self.update_elem(label, prop="element"))(self.driver):
                continue
            for_attr = self.get_attribute(label, bound_by)
            if for_attr:
                linked_flag = any(attr in id_attr for attr in for_attr.split())
                if linked_flag:
                    print("\nlinked_flag for elem", elem)
                    self.label_elements.remove(label)
                    return True
        return False

    def _find_labels_descendants(self):
        """
        Simply collect labels - potential checkbox labels
        """
        label_elements = self.locator.get_all_by_xpath(self.driver, "//label")
        for label in label_elements:
            descendants = label.find_by_xpath("./descendant::*", self.driver)
            descendants = set(map(lambda elem: elem.get_selector(), descendants))
            self.labels_descendants.update(descendants)

    # TODO sew into CompoundJavascriptEngager
    def update_elem(self, elem: Element, prop="framework_element"):
        selector = elem.get_selector()
        element = self.driver.execute_script("return document.querySelector(arguments[0]);", selector)
        framework_element = Element(element, self.driver)

        return locals().get(prop)
