import time

from selenium import webdriver, common
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.detector import Detector


framework_version = 2
WCAG = '3.2.1'
name = "Ensures that when any component receives focus, it does not initiate a change of context"
elements_type = ""
webdriver_restart_required = True
test_data = [
    {
        "page_info": {
            "url": "on_focus/page_bug_on_focus_1.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "on_focus/page_bug_on_focus_2.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "on_focus/page_bug_on_focus_3.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "on_focus/page_bug_on_focus_4.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "on_focus/page_good_on_focus.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "on_focus/page_good_on_focus_2.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "on_focus/page_on_focus.html"
        },
        "expected_status": "NOELEMENTS"
    },
]

DELAY_AFTER_ACTION = 2
MAXIMUM_DEPTH_OF_VERIFICATION = 20000


class Tester:
    def __init__(self, webdriver: webdriver.Chrome, activity):
        self.driver = webdriver
        self.activity = activity
        self.detector = Detector(webdriver)
        self.ignore_elements = self.detector.variable_elements
        self.replica = [e for e in self.detector.get_replica() if e not in self.ignore_elements]

    def testing_load(self):
        """
        checks that the window that captures focus and so on did not open when loading
        :return: string - loading incident if there is one
        """
        time.sleep(DELAY_AFTER_ACTION)
        prev_url = self.driver.current_url

        try:
            self.driver.switch_to.alert.dismiss()
            return "ALERT"
        except common.exceptions.NoAlertPresentException:
            pass

        if (self.driver.current_url != prev_url and
                Element.is_same_page(self.driver.current_url, prev_url)):
            self.activity.get(self.driver)
            return "NEWPAGE"

        if len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return "NEWTAB"

    def onfocus_blur_attribute(self):
        """
        check onFocus attribute
        :param elements: list of webElement
        :return: bool
        """
        return self.driver.execute_script("""
            var resultInfo = [];
            function checkOnFocusAttr(e) {
                var elements = e.querySelectorAll("*");
                Array.prototype.forEach.call(elements, elem => {
                    var onFocusAttr = elem.getAttribute("onfocus");
                    if (onFocusAttr && onFocusAttr.includes("this.blur()")) {
                        resultInfo.push(elem);
                    }
                });
            }
            checkOnFocusAttr(document.body);
            return resultInfo;
        """)

    def action(self, previous_difference):
        """
        if there was any action or content change after the tab on the element, returns this action
        :return: string or None
        """
        prev_url = self.driver.current_url

        # check alert
        if Element._dismiss_alert(self.driver):
            return "ALERT", []

        # check new tab
        if Element._check_if_new_tab_opened(self.driver) is not None:
            return "NEWTAB", []

        # check change page
        if self.driver.current_url != prev_url:
            self.activity.get(self.driver)
            return "NEWPAGE", []

        new_replica = self.detector.get_replica()
        current_difference = [e for e in new_replica if e not in self.replica and e not in self.ignore_elements]
        if [elem for elem in current_difference if elem in previous_difference]:
            self.ignore_elements.extend([elem for elem in current_difference if elem in previous_difference])
            self.replica = [e for e in new_replica if e not in self.ignore_elements]
            return "DOM", current_difference
        return None, current_difference


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):
    time1 = time.time()
    activity.get(webdriver_instance)
    tester = Tester(webdriver_instance, activity)
    body = webdriver_instance.find_elements_by_xpath("//body")[0]

    if tester.testing_load() is not None:
        return {'status': 'FAIL',
                'message': '',
                'elements': [{
                    'element': body,
                    'problem': "Failure of Success Criterion 3.2.1 due to opening a new window as soon as a new page is loaded"
                }],
                'checked_elements': []}

    conclusion = {'status': "NOELEMENTS", 'message': '', 'elements': [], 'checked_elements': []}

    elements_with_onfocus_attribute_blur = tester.onfocus_blur_attribute()
    if elements_with_onfocus_attribute_blur:
        for elem in elements_with_onfocus_attribute_blur:
            el = Element(elem, webdriver_instance)
            conclusion['checked_elements'].append(el)
            conclusion['elements'].append({'element': el,
                                           'problem': "Failure of Success Criteria 3.2.1 due to using script to "
                                                      "remove focus when focus is received",
                                           'error_id': "OnFocus"})
    if conclusion['checked_elements']:
        conclusion['status'] = 'PASS'
    if conclusion['elements']:
        conclusion['status'] = 'FAIL'

    try:
        body.send_keys(Keys.TAB)
        time.sleep(DELAY_AFTER_ACTION)
    except WebDriverException:
        print(conclusion)
        return conclusion

    first_focusable = webdriver_instance.switch_to.active_element
    if first_focusable == body:
        print(conclusion)
        return conclusion

    previous_element = first_focusable
    previous_difference = []
    counter = 1
    while True:
        print(f'\rAnalyzing elements {counter}', end="", flush=True)
        counter += 1

        # tab through all the elements until we get back to the beginning
        try:
            res_focus_prev, previous_difference = tester.action(previous_difference)
            elem = Element(previous_element, webdriver_instance)
            if res_focus_prev is not None:
                conclusion['elements'].append({'element': elem,
                                               'problem': "Failure of Success Criteria 3.2.1: changes of content during"
                                                          " the focus on the subject",
                                               'error_id': "OnFocus"})

            if elem in conclusion['checked_elements'] or previous_element.location['y'] > MAXIMUM_DEPTH_OF_VERIFICATION:
                break

            if previous_element.tag_name in ("body", "html"):  # Fake focus
                conclusion['checked_elements'].append(elem)
                previous_element.send_keys(Keys.TAB)
                time.sleep(DELAY_AFTER_ACTION)
                continue

            conclusion['checked_elements'].append(elem)

            try:
                previous_element.send_keys(Keys.TAB)
                time.sleep(DELAY_AFTER_ACTION)
            except WebDriverException as e:
                break

            previous_element = webdriver_instance.switch_to.active_element
        except WebDriverException:
            continue

    if not conclusion['checked_elements']:
        conclusion['status'] = 'NOELEMENTS'
    elif conclusion['elements']:
        conclusion["status"] = "FAIL"
    else:
        conclusion["status"] = "PASS"
    print(f"test_on_focus timer = {time.time() - time1}")
    print(conclusion)
    return conclusion
