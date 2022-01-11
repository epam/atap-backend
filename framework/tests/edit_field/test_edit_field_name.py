from selenium.common.exceptions import NoSuchElementException, UnexpectedAlertPresentException, \
    ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys

from framework.element import Element, ElementLostException
from framework.element_locator import ElementLocator
from framework.libs.test_pattern import SuperTest

# from framework.libs.test_pattern import wrap_test_output

framework_version = 0  # Detecting test
locator_required_elements = []
depends = []
webdriver_restart_required = True
name = "Ensures that edit fields have programmatically determined name"
WCAG = "4.1.2"
elements_type = "edit field"
test_data = [
    {
        "page_info": {
            "url": r"page_good_edit_fields.html"
        },
        "expected_status": "PASS"
    },
]
DISABLED = ("hidden", "readonly", "disabled")
TOLERANCE = 20


# @wrap_test_output
def test(webdriver_instance, activity, element_locator: ElementLocator):
    return EditField(webdriver_instance, activity, element_locator).get_result()


class EditField(SuperTest):
    def __init__(self, webdriver_instance, activity, element_locator):
        super(EditField, self).__init__(webdriver_instance, activity, element_locator, dependencies=None)
        self.edit_fields = {
            "by_tag": [],
            "by_attribute": []
        }
        self.possible_labels = {
            "for": {},
            "id": {}
        }
        self.result = {
            "status": "NOELEMENTS",
            "message": "There are no edit fields",
            "elements": [],
            "checked_elements": [],
            "active_fields": [],  # of (field, label_text)
        }
        self.main()

    def main(self):
        if not self.collect_edit_fields():
            return
        self.set_pass_status()
        self.collect_connections()
        self.find_field_text()

    def collect_edit_fields(self):
        """ Collect all edit fields on the Web page. Return bool value of elements detection

        """
        xpath_by_tag = f"//input[@type='text' or @type='number' or @type='email' or @type='tel' or @type='password' or " \
                       f"@type='search' or @type='url' or @type='']|//textarea"
        xpath_by_attribute = f"//*[@contenteditable='true']"
        self.edit_fields["by_tag"].extend(self.locator.get_all_by_xpath(self.driver, xpath_by_tag))
        self.edit_fields["by_attribute"].extend(self.locator.get_all_by_xpath(self.driver, xpath_by_attribute))
        if self.edit_fields["by_tag"] or self.edit_fields["by_attribute"]:
            self.result["status"] = "PASS"
            self.result["message"] = "Edit fields have appropriated names"
            return True
        else:
            return False

    def collect_connections(self):
        """ Collect attributes that may be used to set element name - connect an edit field and a label.

        """
        elements_with_id = self.locator.get_all_by_xpath(self.driver, "//*[@id]")
        for element in elements_with_id:
            self.possible_labels["id"].update({element.get_attribute(self.driver, "id"): element})  # {value: element}
        elements_with_for = self.locator.get_all_by_xpath(self.driver, "//*[@for]")
        for element in elements_with_for:
            self.possible_labels["for"].update({element.get_attribute(self.driver, "for"): element})  # {value: element}

    def find_field_text(self):
        all_edit_fields = []
        for type_ in self.edit_fields.values():
            all_edit_fields.extend(type_)
        all_edit_fields = list(set(all_edit_fields))
        Element.safe_foreach(all_edit_fields, self.check_field)

    def check_field(self, field):
        if self.is_disabled(field) or field.get_attribute(self.driver, "type") in\
                ("file", "radio", "button", "checkbox", "hidden", "reset", "submit", "radio"):
            return
            # By some strange reason another input types also may be added and should be ignored
        field_data = self.get_element_attributes(field)
        self.result["checked_elements"].append(field)
        if field_data["id"] not in self.possible_labels["for"].keys() and \
                not field_data["aria-label"] and not field_data["title"] and \
                field_data["aria-labelledby"] not in self.possible_labels["id"].keys() and \
                field_data["aria-describedby"] not in self.possible_labels["id"].keys() and \
                field_data["parent_tag_name"] != "label" and not field_data['placeholder']:
            field_label_text = ""
        else:
            field_label_text = self.get_label_text(field, field_data)

        self.result["active_fields"].append((field, field_label_text))

    def get_element_attributes(self, element: Element):
        attributes = {"id": self.get_attribute(element, "id"),
                      "title": self.get_attribute(element, "title"),
                      "aria-label": self.get_attribute(element, "aria-label"),
                      "aria-labelledby": self.get_attribute(element, "aria-labelledby"),
                      "aria-describedby": self.get_attribute(element, "aria-describedby"),
                      "parent_tag_name": element.get_parent(self.driver).tag_name,
                      "placeholder": self.get_attribute(element, "placeholder"),
                      'label': self.get_connected_label_text(element),
                      }
        return attributes

    def get_connected_label_text(self, element) -> str:
        id_ = self.get_attribute(element, 'id')
        if not id_:
            return ''
        label_text = ''
        labels = self.driver.find_elements_by_xpath(f'//*[@for = "{id_}"]')
        """ ^ Sometimes site developers makes multiple labels for one element."""
        for label in labels:
            label_text += ' ' + Element(label, self.driver).get_text(self.driver)
        return label_text

    def get_label_text(self, field, field_data):
        text = ""
        parent = field.get_parent(self.driver)
        if parent.tag_name == "label":
            text += parent.get_text(self.driver)
        if field_data["placeholder"]:
            try:
                text += field_data["placeholder"]
            except KeyError:
                pass
        if field_data["id"]:
            try:
                text += self.possible_labels["for"][field_data["id"]].get_text(self.driver)
            except KeyError:
                pass
        if field_data["aria-labelledby"]:
            try:
                text += self.possible_labels["id"][field_data["aria-labelledby"]].get_text(self.driver)
            except KeyError:
                pass
        if field_data["aria-describedby"]:
            try:
                text += self.possible_labels["id"][field_data["aria-describedby"]].get_text(self.driver)
            except KeyError:
                pass
        if field_data['label']:
            try:
                text += field_data['label']
            except KeyError:
                pass
        text += self.get_form_alert_text(field)
        text += self.get_nearest_words(field)
        return text.lower()

    def get_form_alert_text(self, element: Element):
        """ If an edit field in a <form> checks changes in a DOM to detect alerts about the field requirements.

        :return: text of alerts
        """
        self.page_refresh()
        text = ""
        try:
            form_parent = element.find_by_xpath("ancestor::form", self.driver)[0]
        except NoSuchElementException:
            return ""
        except IndexError:
            return ""

        start_form_elements = form_parent.find_by_xpath("descendant::*", self.driver)
        action = element.click(self.driver)["action"]
        if action == "NONINTERACTABLE":
            return ""
        try:
            element.get_element(self.driver).send_keys(Keys.TAB)
        except ElementNotInteractableException:
            return ""
        element.click(self.driver)
        end_form_elements = form_parent.find_by_xpath("descendant::*", self.driver)

        different_elements = list(set(end_form_elements) - set(start_form_elements))

        if different_elements:
            for diff_elem in different_elements:
                alert_text = diff_elem.get_text(self.driver)
                try:
                    text.index(alert_text)
                except ValueError:
                    if len(alert_text) < 50:
                        text += alert_text
        return text

    def page_refresh(self):
        """ Completely refresh the page"""
        try:
            self.driver.refresh()
        except UnexpectedAlertPresentException:
            pass
        self.activity.get(self.driver)

    def is_disabled(self, element: Element):
        html = self.get_element_html(element)
        for key in DISABLED:
            try:
                html.index(key)
                return True
            except ValueError:
                continue
        return False

    def get_element_html(self, element: Element):
        """Return html that describes the element itself (like '<div foo bar baz>', without innerHTML and </div>)

        """
        try:
            outer_html = element.get_element(self.driver).get_attribute("outerHTML")
            for num, symbol in enumerate(outer_html):
                if symbol == ">":
                    return outer_html[:num + 1]
        except (StaleElementReferenceException, ElementLostException):
            element_html = element.source[:element.source.index(">") + 1:]
            return element_html

    def get_nearest_words(self, element: Element):
        text = ""
        parent = element.get_parent(self.driver)
        near_elements = parent.find_by_xpath('descendant::*', self.driver)
        for elem in near_elements:
            text += elem.get_text(self.driver).lower()
        return text
