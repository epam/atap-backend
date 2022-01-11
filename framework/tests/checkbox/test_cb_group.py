from framework.element import Element, ElementLostException
from framework.libs.test_pattern import SuperTest
from framework.js_conductor import CompoundJavascriptEngager, eval_js
from .checkbox_scripts import (
    execute_on_promise_script,
    jquery_check_script,
    illegal_label_script,
    group_verification_script,
)

from selenium.common.exceptions import JavascriptException, StaleElementReferenceException

from collections import Counter
from copy import deepcopy


framework_version = 4  # TODO 5
WCAG = "1.3.1, 4.1.2, 3.3.2"
name = "Ensure that checkboxes are properly organized in group"
depends = ["test_checkbox_base"]
webdriver_restart_required = True
elements_type = "checkbox"
test_data = [
    {"page_info": {"url": r"checkbox/page_good_checkbox.html"}, "expected_status": "PASS"},
    {
        "page_info": {"url": r"checkbox/page_bugs_checkbox.html"},
        "expected_status": "FAIL",
        "expected_problem_count": 1,
    },
    # {
    #     "page_info": {
    #         "url": r"checkbox/pretty_checkbox.html"
    #     },
    #     "expected_status": "FAIL",
    #     "expected_problem_count": 3
    # }  # quite heavy
]
test_message = "Some checkboxes group parent element doesn't have role, no fieldset or legend either"


def test(webdriver_instance, activity, element_locator, dependencies):
    """
    Test on group organization of checkboxes like elements.
    Ensures group will be recognized by NVDA.
    """
    return CheckboxTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class CheckboxTest(SuperTest, CompoundJavascriptEngager):
    def __init__(self, webdriver_instance, activity, locator, dependencies, timeout=4):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.framework_element = None
        self.group_elements = self.dependency_data[depends[0]]["dependency"].copy()
        scripts = [execute_on_promise_script, jquery_check_script, illegal_label_script, group_verification_script]
        script_names = ["onPromise", "jQuery", "textLabels", "groupTest"]
        super().__init__(
            webdriver_instance,
            activity,
            locator,
            dependencies,
            scripts=scripts,
            script_names=script_names,
            timeout=timeout,
        )
        self.body_boxes = set()  # single checkboxes pop up to <body>
        self._main()

    def _main(self):
        print("\ngroup_elements are", self.group_elements)
        # handle special cases
        if not self.group_elements:
            self.result["status"] = "NOELEMENTS"
            self.result["message"] = "No checkbox elements"
            self.result["elements"] = []
        elif self.group_elements.__len__() == 1:
            print("\nThe only checkbox")
            self.set_pass_status()
            self.result["message"] = "Found the only checkbox - no group needed"
        else:
            # main case
            self.set_pass_status()
            # now register js
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
                "groupTest",
                recorder=self.fetch_script_source,
                evaluator=self.execute_script_eval,
            )

            corrected_checkboxes = self.driver.execute_script(
                """
                return window.correctedCheckboxes(arguments[0]);
                """,
                [
                    [
                        *map(
                            lambda elem: self.update_elem(elem, prop="element"),
                            boxes,
                        )
                    ]
                    for boxes in self.group_elements.values()
                ],
            )
            # fill back checkboxes if no corrected can be found
            for i, box in enumerate(self.group_elements.values()):
                if not corrected_checkboxes[i]:
                    corrected_checkboxes[i] = self.update_elem(box[-1], prop="element")

            print("\n************************corrected_checkboxes", corrected_checkboxes)
            self.indeterminate = self._collect_indeterminate_toggleall(corrected_checkboxes)

            for i, cb in enumerate(corrected_checkboxes):
                try:
                    corrected_checkboxes[i] = Element(cb, self.driver)
                except (StaleElementReferenceException, ElementLostException):
                    print("\nSTALE corr")
                    corrected_checkboxes[i] = [*self.group_elements.keys()][i]
            print("\ncorrected_checkboxes", corrected_checkboxes)
            self.group_elements = dict(zip(corrected_checkboxes, self.group_elements.values()))
            self.group_elements = {btn: btn for btn in self.group_elements}
            print("\ngroup_elements", self.group_elements)
            # found checkboxes that toggles other checkboxes
            # tie these ones to controller checkbox as group
            if len(self.indeterminate) > 0:
                self._group_with_indeterminate()
            self._find_checkboxes_groups(corrected_checkboxes)
            # filled in mapping from checkbox to its eventual parent

            # get unique groups
            groups = [*self.group_elements.values()]
            group_count = set()
            for elem in groups.copy():
                if elem.get_selector() in group_count:
                    groups.remove(elem)
                group_count.add(elem.get_selector())
            # in case there are single checkboxes on different document level
            if not groups:
                print("\ncheckboxes", corrected_checkboxes)
                checkboxes = deepcopy(corrected_checkboxes)
                # collected checkbox data to test
                print("\ncheckboxes deepcopy", checkboxes)
                self._report_closest_common_parent(corrected_checkboxes, checkboxes)
                print(
                    "********************************\tRESULT NO GROUPS\t********************************\n",
                    self.result,
                )
                return
            # in main case - check criteria and report bugs
            Element.safe_foreach(groups, self._group_role_check)  # checkboxes groups

        print("********************************\tRESULT\t********************************\n", self.result)

    # TODO sew into CompoundJavascriptEngager
    def update_elem(self, elem: Element, prop="framework_element"):
        selector = elem.get_selector()
        element = self.driver.execute_script("return document.querySelector(arguments[0]);", selector)
        framework_element = Element(element, self.driver)

        return locals().get(prop)

    def _report_issue_corrected_group(self, pseudo_group, fail_message, error_id):
        print("\n_report_issue_corrected_group")
        boxes = [
            self.update_elem(box, prop="element")
            for box in self.group_elements
            if self.group_elements.get(box) == pseudo_group
        ]

        print("\nboxes", [Element(el, self.driver) for el in boxes])
        print("pseudo_group", pseudo_group)

        first_index = 0  # FIXME tmp
        try:
            true_group_listed = self.driver.execute_script(
                """
                return window.findLesserGroups(arguments[0], arguments[1]);
            """,
                boxes,
                self.update_elem(pseudo_group, prop="element"),
            )  # what a bug
            if not len(true_group_listed):
                raise JavascriptException
        except JavascriptException:
            try:
                first_index = -1  # FIXME tmp
                boxes.reverse()
                true_group_listed = self.driver.execute_script(
                    """
                    return window.findLesserGroups(arguments[0], arguments[1]);
                """,
                    boxes,
                    self.update_elem(pseudo_group, prop="element"),
                )
            except JavascriptException:
                true_group_listed = [
                    boxes,
                ]

        # place text nodes back to document instead of tmp created span element wrappers
        self.driver.execute_script("window.rollbackSpanTexts();")

        to_report_elements = set()

        for group in true_group_listed:
            group_boxes = [Element(cb, self.driver).get_selector() for cb in group]
            group_boxes.extend(
                [ind.get_selector() for ind in self.indeterminate if self.group_elements.get(ind) == pseudo_group]
            )

            # FIXME
            # temporary return first checkbox

            issue_elem = Element(self.driver.find_element_by_css_selector(group_boxes[first_index]), self.driver)
            if not issue_elem in to_report_elements:
                self.report_issue(
                    issue_elem,
                    f"{fail_message} for checkboxes {group_boxes}",
                    error_id,
                    "FAIL",
                    test_message,
                )
                to_report_elements.add(issue_elem)

        # self.report_issue(
        #     pseudo_group, f"{fail_message} for checkboxes {group_boxes}", error_id, "FAIL", test_message
        # )

    def _find_checkboxes_groups(self, checkboxes):
        """
            Recursively fills values of self.group_elements in with
            most likely parent elements. Best solution for grouped checkboxes.
        Args:
            checkboxes (list): keys of self.group_elements
        Returns:
            Recursion ends if all checkboxes are organized in groups (2 and more for one)
                or some outstanding cb group popped up right to <body>
        """
        print("********************************")
        print("_find_checkboxes_groups")
        print("checkboxes", checkboxes)
        if not [*filter(lambda cb: self.group_elements.get(cb).tag_name != "body", checkboxes)]:
            print("not checkboxes or all are <body>")
            print("group_elements", self.group_elements.values())
            return
        print("checkboxes FOR")
        for btn in checkboxes.copy():
            group = self.group_elements[btn]
            group = group if group.tag_name == "body" else group.get_parent(self.driver)
            print("group", group)
            print("self.group_elements[btn] = group")
            self.group_elements[btn] = group
        print("checkboxes OUTTA FOR")
        print("Counter", Counter(map(lambda el: el.get_selector(), self.group_elements.values())).most_common())
        group_parents = dict(
            filter(
                lambda num: num[1] <= 1,
                Counter(map(lambda el: el.get_selector(), self.group_elements.values())).most_common(),
            )
        ).keys()
        print("\ngroup_parents", group_parents)
        print("comprehension")
        checkboxes = [btn for btn in checkboxes if self.group_elements[btn].get_selector() in group_parents]
        print(checkboxes)
        return self._find_checkboxes_groups(checkboxes)

    def _group_with_indeterminate(self):
        print("\n_group_with_indeterminate")
        ind_groups = {}
        lesser_group = None

        for ind in self.indeterminate:
            group = ind
            print("ind", ind)
            ind_boxes = self.indeterminate[ind]
            while (
                set(group.find_by_xpath("./descendant::*", self.driver)).intersection(ind_boxes).__len__()
                != ind_boxes.__len__()
            ):
                lesser_group = group
                group = group.get_parent(self.driver)
            print("group", group)
            for box in ind_boxes + [ind]:
                self.group_elements[box] = lesser_group

        print("group_elements", self.group_elements)

    def _group_text_label(self, group):
        checkboxes = [cb for cb in self.group_elements if self.group_elements.get(cb) == group]
        checkboxes = [*map(lambda elem: self.update_elem(elem, prop="element"), checkboxes)]
        # checkboxes localized as buttons without text, inputs prioritized

        text_labels = self.driver.execute_script(
            """
            return window.getCheckboxLabel(arguments[0]);""",
            checkboxes,
        )

        return self.driver.execute_script(
            """return window.getGroupLabel
                (arguments[0], arguments[1], arguments[2], arguments[3]);
            """,
            self.update_elem(group, prop="element"),
            [*map(lambda elem: self.update_elem(elem, prop="element"), self.group_elements.values())],
            checkboxes,
            text_labels,
        )

    def _is_labelled_by(self, element, checkbox_group):
        labelled = self.get_attribute(element, "aria-labelledby")
        if labelled:
            print("labelledby", labelled)
        else:
            checkboxes = [cb for cb in self.group_elements if self.group_elements.get(cb) == checkbox_group]
            labelled = [
                self.get_attribute(desc, "aria-labelledby")
                for desc in checkbox_group.find_by_xpath("descendant::*", self.driver)
            ]
            if len([*filter(None, labelled)]) >= len(checkboxes):
                return True
        return False

    def _group_role_check(self, group: Element, checkbox_group=None):
        """
        Check the validity of checkbox group,
        group is taken from self.group_elements
        Group must have role or be legend or fieldset
        Group must not be decorated as text node nearby on top
        """
        print("********************************")
        print("_group_role_check")
        checkbox_group = checkbox_group or group
        print("group", group)
        print("checkbox_group", checkbox_group)
        fail_message = "Checkboxes has no group identificator: bug 1.3.1, 4.1.2"
        error_id = "CheckboxGroupLost"
        if group.tag_name == "body":
            if not self.body_boxes:
                self.body_boxes.update(
                    {cb: group for cb, group in self.group_elements.items() if group.tag_name == "body"}.keys()
                )
                print("\nbody boxes", self.body_boxes)
            if self.body_boxes.__len__() == 1:
                print("\nbody boxes skip")
                return
            else:
                print("\nbody can be a group")

        if self.get_attribute(group, "role") == "group":
            print('attribute(group, role) == "group"')
            aria_label = self.get_attribute(group, "aria-label")
            if aria_label:
                print("\nthere is aria-label")
                return
            if self._is_labelled_by(group, checkbox_group):
                print("labelledby role group")
                return
            else:
                print('attribute(group, role) == "group" but no label')
                fail_message = "The element group has role, but no label: bug 1.3.1, 4.1.2"
                error_id = "CheckboxGroupLabelledBy"

                try:
                    maybe_label = self._group_text_label(checkbox_group)
                except JavascriptException:
                    maybe_label = None
                print("\nmaybe_label", Element(maybe_label, self.driver)) if maybe_label else 1
                print("return FAIL")
                if maybe_label:
                    fail_message = "The element has incorrect label: bug 3.3.2, 4.1.2"
                    error_id = "CheckboxGroupLabelOff"
                self._report_issue_corrected_group(checkbox_group, fail_message, error_id)
                return
        if group.tag_name == "fieldset":
            legend = group.find_by_xpath("./legend", self.driver)
            if legend and legend[0].get_text(self.driver):
                print("\nlegend")
                return
            else:
                fail_message = "The element group has no legend: bug 1.3.1, 4.1.2"
                error_id = "CheckboxGroupLegend"
                try:
                    maybe_label = self._group_text_label(checkbox_group)
                except JavascriptException:
                    maybe_label = None
                print("\nmaybe_label legend", Element(maybe_label, self.driver)) if maybe_label else 1
                if maybe_label:
                    fail_message = "The element has incorrect label: bug 3.3.2, 4.1.2"
                    error_id = "CheckboxGroupLabelOff"
            self._report_issue_corrected_group(checkbox_group, fail_message, error_id)
            return

        if self._is_labelled_by(group, checkbox_group):
            print("labelledby")
            return

        group_parent = group if group.tag_name == "body" else group.get_parent(self.driver)
        while group_parent.tag_name != "body":
            print("while cycle", group_parent)
            return self._group_role_check(group_parent, checkbox_group)
        print("\nAFTER WHILE")
        print("group", group)
        print("checkbox_group", checkbox_group)
        try:
            maybe_label = self._group_text_label(checkbox_group)
        except JavascriptException:
            maybe_label = None
        print("\nmaybe_label", Element(maybe_label, self.driver)) if maybe_label else 1
        if maybe_label:
            fail_message = "The element has incorrect label: bug 3.3.2, 4.1.2"
            error_id = "CheckboxGroupLabelOff"
        self._report_issue_corrected_group(checkbox_group, fail_message, error_id)

    def _collect_indeterminate_toggleall(self, checkboxes):
        print("\n_collect_indeterminate_toggleall")
        indeterminate_map = self.driver.execute_script(
            """return window.whichIndeterminate(arguments[0]);""",
            checkboxes,
        )
        indeterminate_boxes = [None] * len(indeterminate_map)

        for i in range(len(indeterminate_map)):
            ind = [*filter(lambda ind: hasattr(ind, "get"), indeterminate_map[i])][0].get("indeterminate")
            indeterminate_boxes[i] = Element(ind, self.driver)
            print("ind", indeterminate_boxes[i])
            indeterminate_map[i] = [
                Element(elem, self.driver) for elem in indeterminate_map[i] if not hasattr(elem, "get")
            ]

        indeterminate_map = dict(zip(indeterminate_boxes, indeterminate_map))
        print("indeterminate_map", indeterminate_map)

        return indeterminate_map

    def _report_closest_common_parent(self, checkboxes, checkboxes_copy):
        """
        If checkboxes didn't get their group till here,
        it will report the smallese container that contains them all
        """
        print("********************************")
        print("_report_closest_common_parent")
        common_group = Counter()
        print("common_group", common_group)
        while True:
            print("\nwhile True")
            checkboxes = deepcopy(checkboxes_copy)
            checkboxes_copy = []
            print("\ncheckboxes", checkboxes)
            print("\ncheckboxes_copy", checkboxes_copy)
            print("checkboxes FOR")
            for checkbox in checkboxes:
                parent = checkbox.get_parent(self.driver)
                common_group.update([parent.get_selector()])
                checkboxes_copy.append(parent)
                print("parent", parent)
                print("common_group", common_group)
                print("checkboxes_copy", checkboxes_copy)
            print("\nany(c > 1 for c in common_group.values())", any(c > 1 for c in common_group.values()))
            if any(c > 1 for c in common_group.values()):
                problems = [key for key, value in common_group.items() if value > 1]
                print("\nproblems", problems)
                print("problems FOR")
                for problem in problems:
                    print("pop problem", common_group)
                    common_group.pop(problem)
                    checkboxes_copy = [group for group in checkboxes_copy if group.get_selector() != problem]
                    print("checkboxes_copy", checkboxes_copy)
                    problem = self.driver.execute_script("return document.querySelector(arguments[0]);", problem)
                    print("\nproblem element", Element(problem, self.driver))
                    self._report_issue_corrected_group(
                        Element(problem, self.driver),
                        "Checkboxes has no group identificator: bug 1.3.1, 4.1.2",
                        "CheckboxGroupLost",
                    )
            if not checkboxes_copy or any(g.tag_name == "body" for g in checkboxes_copy):
                print("\nnot checkboxes_copy", not checkboxes_copy)
                print(
                    '\nany(g.tag_name == "body" for g in checkboxes_copy)',
                    any(g.tag_name == "body" for g in checkboxes_copy),
                )
                print("BREAK")
                break
