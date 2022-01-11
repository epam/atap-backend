from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.test_pattern import SuperTest

__all__ = []

framework_version = 4
WCAG = "4.1.2"
name = "Ensure that disclosure buttons have correct attributes"
depends = ["test_dd_detector"]
webdriver_restart_required = False
elements_type = "button"
test_data = [
    {
        "page_info": {"url": r"dropdowns/page_good_disclosure.html"},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"dropdowns/page_bugs_disclosure.html"},
        "expected_status": "FAIL"
    },
]
test_message = "Some selector buttons doesn't have appropriate ARIA role and/or" \
               "doesn't able to receive focus using keyboard"
INTERACTIVE_ELEMENTS_TAGS = ('a', 'button', 'input', 'textarea')


def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return SelectorButtonRole(webdriver_instance, activity, element_locator, dependencies).get_result()


class SelectorButtonRole(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.dropdowns = self.dependency_data[depends[0]]["dependency"]
        if self.dropdowns:
            self.set_pass_status()
        self._main()

    def _main(self):
        Element.safe_foreach(list(self.dropdowns.keys()), self._check)

    def _check(self, button):
        data = self.dropdowns[button]
        if data['type'] != 'disclosure':
            return
        popup_elements = data["dd_elements"]
        self.result["checked_elements"].append(button)

        if button.tag_name not in ("button", "a") and \
                self.get_attribute(button, "role") not in ("button", "link") and \
                self.get_attribute(button, "tabindex") == 0 and \
                self.get_attribute(button, "aria-expanded") in ('false', "true"):
            # 1. WCAG 4.1.2
            self.report_issue(
                button,
                "A disclosure button have incorrect ARIA role",
                "DisclosureAriaRole",
                "FAIL",
                test_message,
            )

        if (button.tag_name in ("button", "a") or self.get_attribute(button, "role") in ("button", "link")) and \
                self.get_attribute(button, "aria-expanded") in ('false', "true") and \
                self.get_attribute(button, "tabindex") not in (0, None):
            # 3. WCAG 2.1.1
            self.report_issue(
                button,
                "A disclosure button have incorrect tabindex",
                "DisclosureTabindex",
                "FAIL",
                test_message,
            )

        if button.tag_name not in ("button", "a") and \
                self.get_attribute(button, "role") not in ("button", "link") and \
                self.get_attribute(button, "aria-expanded") not in ('false', "true") and \
                self.get_attribute(button, "tabindex") == 0:
            # 4. WCAG 4.1.2
            self.report_issue(
                button,
                "A disclosure button have incorrect ARIA attributes",
                "DisclosureAriaAttributes",
                "FAIL",
                test_message,
            )

        if (button.tag_name not in ("button", "a") and self.get_attribute(button, "role") not in ("button", "link")) or\
                self.get_attribute(button, "aria-expanded") not in ('false', "true") and \
                self.get_attribute(button, "tabindex") != 0:
            # 5. WCAG 2.1.1 and 4.1.2
            self.report_issue(
                button,
                "A disclosure button have incorrect ARIA attributes",
                "DisclosureAllAttributes",
                "FAIL",
                test_message,
            )

        if button.tag_name in ("button", "a") and self.get_attribute(button, "tabindex") == -1:
            # 6. WCAG 2.1.1
            self.report_issue(
                button,
                "A disclosure button have incorrect tabindex",
                "DisclosureNegativeTabindex",
                "FAIL",
                test_message,
            )

        # last one
        if (button.tag_name in ("button", "a") or self.get_attribute(button, "role") in ("button", "link")) and \
                self.get_attribute(button, "tabindex") == 0:

            if self.get_attribute(button, "aria-expanded") != 'false':
                # 2. WCAG 4.1.2
                self.report_issue(
                    button,
                    "A disclosure button have incorrect aria-expanded attribute",
                    "DisclosureAriaExpanded",
                    "FAIL",
                    test_message,
                )
            button.click(self.driver)
            if self.get_attribute(button, "aria-expanded") != 'true':
                # 2. WCAG 4.1.2
                self.report_issue(
                    button,
                    "A disclosure button have incorrect aria-expanded attribute",
                    "DisclosureAriaExpanded",
                    "FAIL",
                    test_message,
                )
        self.check_popup(button, popup_elements)

    def check_popup(self, button, popup_elements):
        self._page_refresh()
        button.click(self.driver)
        current_element = Element(self.driver.switch_to_active_element(), self.driver)
        if current_element not in [button] + popup_elements:
            if self.get_attribute(button, "aria-expanded") != 'true':
                # 7. WCAG 2.4.3
                self.report_issue(
                    button,
                    "A disclosure button have incorrect navigation behavior",
                    "DisclosurePopupNavigation",
                    "WARN",
                    test_message,
                )
        self.send_keys(current_element, Keys.TAB)
        if current_element not in [button] + popup_elements:
            if self.get_attribute(button, "aria-expanded") != 'true':
                # 7. WCAG 2.4.3
                self.report_issue(
                    button,
                    "A disclosure button have incorrect navigation behavior",
                    "DisclosurePopupNavigation",
                    "WARN",
                    test_message,
                )
