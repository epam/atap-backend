from selenium import webdriver
from framework.element import Element
import time

from framework.element_locator import ElementLocator
from . import common_modal
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException

framework_version = 4
elements_type = 'modal windows'
WCAG = '2.1.2'

name = "Test for correct closing modal window"
depends = ["test_disguised_modal"]
webdriver_restart_required = True

test_data = [
    {
        "page_info": {
            "url": "modal/page_good_modal.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "modal/page_bugs_modal.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


'''
This test is developed to detect modal windows on a page (in its particular state).
After finding the modal window, a test is run to check for the presence of the correct button to close it.

'''


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    elements = []
    result = 'Problems with modal closing not found'
    status = 'PASS'

    activity.get(webdriver_instance)
    activators = dependencies["test_disguised_modal"]["activators"]
    activators_and_modals = dependencies["test_disguised_modal"]["modals"]
    for activator in activators:
        activator.click(webdriver_instance)
        time.sleep(0.5)
        modals = activators_and_modals[activator]
        if modals:
            modal = modals[0]
            if not modal_is_closing_by_click(modal.get_element(webdriver_instance)):
                element = {
                    "element": modal,
                    "severity": 'FAIL',
                    "interaction_sequence": [{
                        "element": activator,
                        "action": "click"
                    }],
                }
                elements.append(element)

    if len(elements) > 0:
        result = 'Some problems with modal closing dialog found'
        status = 'FAIL'

    if len(activators) == '0':
        status = "NOELEMENTS"

    return {
        "status": status,
        "message": result,
        "elements": elements,
        "checked_elements": activators
    }


def modal_is_closing_by_click(modal):
    is_closing = False
    children_btn = modal.find_elements_by_xpath(".//button")
    children_role_btn = modal.find_elements_by_xpath('.//*[@role="button"]')
    children_submit = modal.find_elements_by_xpath('.//*[@type="submit"]')
    children = children_btn + children_role_btn + children_submit
    for i in reversed(range(len(children))):
        try:
            children[i].click()
        except (ElementNotInteractableException, ElementClickInterceptedException):
            print('ElementNotInteractableException')
            continue
        time.sleep(1)
        if modal.size['height'] == 0:
            is_closing = True
            break
    return is_closing

