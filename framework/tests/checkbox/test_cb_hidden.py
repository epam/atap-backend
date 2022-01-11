from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import alert_is_present, visibility_of
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException

from framework.element import Element
from framework.element_wrapper import ElementWrapper
from framework.libs.test_pattern import SuperTest


framework_version = 4
WCAG = "2.1.1"
name = "Warns invisible buttons, which couldn't be accessed through keyboard"
depends = ["test_checkbox_base"]
webdriver_restart_required = True
elements_type = "checkbox"
test_data = [
    {
        "page_info": {
            "url": r"checkbox/page_good_checkbox.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": r"checkbox/page_bugs_checkbox.html"
        },
        "expected_status": "WARN",
        "expected_problem_count": 1
    },
]
test_message = """Some elements aren't able to receive focus through keyboard,\
                    but have invisible checkboxes: bug 2.1.1"""


def test(webdriver_instance, activity, element_locator, dependencies):
    """
    Test on accessibility of elements that behave like checkboxes. 
    """
    return KeyboardHiddenTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class KeyboardHiddenTest(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.framework_element = None
        self.buttons = self.dependency_data[depends[0]]["dependency"].copy()
        self._main()
    
    def _main(self):
        if not self.buttons:
            self.result["status"] = "NOELEMENTS"
            self.result["message"] = "No elements like chechbox"
            self.result["elements"] = []
        else:
            self.set_pass_status()
            self.buttons = list(self.buttons.keys())
            self.result["checked_elements"] = self.buttons
            Element.safe_foreach(self.result["checked_elements"], self._keyboard_access_check)
            self._collect_keyboard_issues()

    def _collect_keyboard_issues(self):
        for btn in self.buttons:
            children = btn.find_by_xpath("descendant::*", self.driver) + [btn]
            if btn.tag_name == 'label':
                for_attr = self.get_attribute(btn, 'for')
                if for_attr:
                    children.append(
                        self.locator.get_all_by_xpath(self.driver,
                            f'//input[@id={for_attr} or @name={for_attr}]')[0]
                    )
            hidden_cb = any(child.tag_name == 'input'
                        and self.get_attribute(child, 'type') == 'checkbox'
                        and not visibility_of(child.get_element(self.driver))(self.driver)
                        for child in children)
            if hidden_cb:
                self.report_issue(
                    btn,
                    "An invisible checkbox couldn't be accessed through keyboard: bug 2.1.1",
                    "CheckboxHidden",
                    "WARN",
                    test_message)
                self.result["status"] = "WARN"
    
    def wrap(self, el):
        return ElementWrapper(el, self.driver)
    
    def _is_nested(self, element: Element, box: Element, tol=5):
        """
        Method checks if element is inside box, with tolerance
        """
        box = self.wrap(box)
        element = self.wrap(element)
        left, bottom = tuple(box.location)
        box_width, box_length = tuple(box.size)
        x, y = tuple(element.location)
        width, length = tuple(element.size)
        x_nested = (x > left - tol) and (x - left < box_length - length + tol)
        y_nested = (y > bottom - tol) and (y - bottom < box_width - width + tol)
        return x_nested and y_nested
    
    def _keyboard_access_check(self, element: Element, button_element=None, tol=5):
        """
        Checks web element that is clickable - from buttons,
        if it can be accessed through keyboard from parent <div> or <body>...
        Access is tested by sending TAB key to button elements within parent.
        Check access by getting focus value after TAB and lastly after shift+TAB,
        so buttons within parent could be accessed outside it.
        If tabbed elements in buttons - remove them. 
        If any left in buttons, account each as warning to the test result.
        """
        if not element in self.buttons and element in self.result["checked_elements"]:
            return
        button_element = button_element or element
        parent = element.get_parent(self.driver)
        if parent.tag_name not in ('div', 'body', 'form', 'fieldset', 'ul'):
            return self._keyboard_access_check(parent, button_element)
        active_el = button_element
        tabbed = []
        while True:
            try:
                active_el.get_element(self.driver).send_keys(Keys.TAB)
            except ElementNotInteractableException:
                return
            active_el = self.driver.switch_to.active_element
            active_el = Element(active_el, self.driver)
            within_flag = self._is_nested(active_el, parent)
            if not within_flag or active_el.tag_name == 'body':
                home_back = ActionChains(self.driver)
                home_back.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT)
                home_back.perform()
                active_el = self.driver.switch_to.active_element
                active_el = Element(active_el, self.driver)
                if active_el in tabbed:
                    tabbed.append(button_element)
                    break
                else:
                    return
            tabbed.append(active_el)
        self.buttons = [btn for btn in self.buttons if btn not in tabbed]
        return
