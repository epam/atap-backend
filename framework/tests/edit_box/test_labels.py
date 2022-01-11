from selenium import webdriver
from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper

# from framework.tests.checkbox.test_checkbox_base import parse_html, get_element_opening_tag
# from framework.tests.checkbox.test_cb_label import label_nearby, text_nearby

name = "Ensures that found edit boxes has proper <label>"
WCAG = "1.3.1, 3.3.2"  # ? NOT SURE at the moment
depends = ["test_base_box_editable"]
webdriver_restart_required = False
framework_version = 0
elements_type = "edit field"
test_data = [
    {"page_info": {"url": "edit_boxes/page_base_edit_box.html"}, "expected_status": "PASS"},
    {
        "page_info": {"url": "edit_boxes/page_bugs_edit_box.html"},
        "expected_status": "FAIL",
        "expected_problem_count": 1,
    },
]


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator, dependencies):
    """
    In this test, is "labels" which are not correct decorated,
    however, with great probability associated with edit boxes.

    .. warnings also::
        Just want to clarify that since Axe checks all properly designed "labels",
        and to check the correct design and logic of the work is not possible at the moment,
        we are just looking for not properly designed "labels".
    """
    activity.get(webdriver_instance)
    return LabelsBox(webdriver_instance, element_locator, dependencies).result_dict()


class LabelsBox:
    def __init__(self, driver, locator, dependencies):
        self._dr = driver
        self._locator = locator
        self._dep = dependencies
        self.not_checked = []

    def _wrap(self, element):
        return ElementWrapper(element, self._dr)

    def result_dict(self) -> dict:
        result = {
            "status": "PASS",
            "message": "",
            "elements": [],
            "checked_elements": [],
        }
        boxes = self._main()
        if boxes is None:
            result["status"] = "NOELEMENTS"
            result["message"] = "This page don't have good edit boxes"
        elif boxes:
            result["status"] = "FAIL"
            result["elements"] = boxes
            result["message"] = "Edit boxes on page has problems with labels"
        else:
            result["message"] = "No labels for all found boxes"
        return result

    def _main(self):
        bad_labels = []
        for elem in self._dep["test_base_box_editable"]["working"]:
            el = elem["box"]
            if not el:
                return None
            self.not_checked.append(el)
        self.not_checked = [
            elem
            for elem in self.not_checked
            if elem.tag_name in {"input", "textarea", "select"}
            and not self.get_attribute(elem, "type") in {"button", "submit"}
        ]
        self.skip_fine_labels()
        for elem in self.not_checked.copy():
            bad_label, box = self.satisfactory_label(elem)
            if bad_label is not None:
                bad_labels.append(
                    {"element": bad_label, "problem": f"This label of edit box {box} is not decorated by rules"}
                )
        return bad_labels

    def skip_fine_labels(self):
        """
        Iterate through programmatically defined labels,
        drop edit boxes with such labels present.
        """
        # for bound
        labels = self._locator.get_all_by_xpath(self._dr, "//label")
        left_boxes = [box.get_selector() for box in self.not_checked]
        for_labels = [l for l in labels if self.get_attribute(l, "for")]
        for label in for_labels:
            for_attr = self._wrap(label)["for"]
            bound_el = self._is_bound_by(for_attr, "id") or _is_bound_by(for_attr, "name")
            if bound_el and bound_el.get_selector() in left_boxes:
                box_idx = left_boxes.index(bound_el.get_selector())
                left_boxes.pop(box_idx)
                self.not_checked.pop(box_idx)
        # wrapped
        wrapped_ancestors = {box: set(box.find_by_xpath("./ancestor::*", self._dr)) for box in self.not_checked}
        labels = list(set(labels).difference(for_labels))
        for box in wrapped_ancestors:
            wrapped_labels = wrapped_ancestors.get(box).intersection(labels)
            if wrapped_labels:
                box_idx = left_boxes.index(box.get_selector())
                left_boxes.pop(box_idx)
                self.not_checked.pop(box_idx)
        try:
            del labels, for_labels, wrapped_ancestors, wrapped_labels
        except UnboundLocalError:
            pass
        # aria-labelledby
        labelledby_boxes = self.not_checked
        labelledby_boxes = [
            labelledby_boxes.pop(labelledby_boxes.index(b))
            for b in labelledby_boxes
            if self.get_attribute(b, "aria-labelledby")
        ]
        for box in labelledby_boxes:
            for_attrs = self._wrap(label)["aria-labelledby"].split()
            bound_label = any(self._is_bound_by(attr, "id") for attr in for_attrs)
            if bound_label:
                box_idx = left_boxes.index(bound_label.get_selector())
                left_boxes.pop(box_idx)
                self.not_checked.pop(box_idx)
        # others: title, aria-label and so on
        for box in self.not_checked.copy():
            auxillary_conditions = [
                self.get_attribute(box, "title"),
                self.get_attribute(box, "placeholder"),
                self.get_attribute(box, "aria-placeholder"),
                self.get_attribute(box, "aria-label"),
                self.get_attribute(box, "role"),
            ]
            auxillary_conditions = list(filter(None, auxillary_conditions))
            if not auxillary_conditions:
                return
            auxillary_conditions = list(map(lambda cond: cond != "", auxillary_conditions[:-1])) + [
                auxillary_conditions[-1] not in ["none", "presentation"]
            ]
            if any(auxillary_conditions):
                self.not_checked.remove(box)

    def satisfactory_label(self, el):
        """s
        Method search bad labels by HTML distance.
        Takes elements that are not already checked for label,
        for auxillary confidence.
        Args:
            el (Element)
        Returns:
            Element, None: label element, only if found one
        """
        label = label_nearby(el, self._dr) or text_nearby(el, self._dr)
        if label:
            return label, el
        return None, _

    def get_attribute(self, element, attribute: str):
        return element.get_element(self._dr).get_attribute(attribute)

    def _is_bound_by(self, value, by="id"):
        located = self._locator.get_all_by_xpath(self._dr, f'//*[@{by}="{value}"]')
        if located:
            return located[0]
        return False
