from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from framework.element import Element

import time

from framework.element_locator import ElementLocator
from . import common_modal

'''
This test is developed to detect modal windows on a page (in its particular state).
Detects backdrop and the window itself, checks for certain roles, returns a list of items.

This test is intended to verify that it is not possible to step into
the background during an open modal window.
'''

name = "Test for check modal window focus order"

depends = ["test_disguised_modal"]
webdriver_restart_required = True

framework_version = 4
elements_type = 'modal windows'
WCAG = "2.4.3"

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


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    elements = []
    result = 'Problems with modal focus not found'
    status = 'PASS'

    activity.get(webdriver_instance)

    # modal_activators = common_modal.get_all_activators( activity, webdriver_instance, element_locator )

    activators = dependencies["test_disguised_modal"]["activators"]
    activators_and_modals = dependencies["test_disguised_modal"]["modals"]
    for activator in activators:
        #element_locator.activate_element(activator)
        activator.click(webdriver_instance)
        time.sleep(0.5)
        modals = activators_and_modals[activator]
        if modals:
            modal = modals[0]
            if not focused_element_visually_in_modal(webdriver_instance, modal.get_element(webdriver_instance)):
                element = {
                    "element": modal,
                    "severity": 'FAIL',
                    "interaction_sequence": [{
                        "element": activator,
                        "action": "click"
                    }],
                }
                elements.append(element)
    
    if len(activators) == '0':
        status = "NOELEMENTS"

    if len(elements) > 0:
        result = 'Some problems with modal focus order dialog found'
        status = 'FAIL'

    return {
        "status": status,
        "message": result,
        "elements": elements,
        "checked_elements": activators
    }

#iTOFO: fix it later
def focused_element_in_modal(webdriver_instance, modal):
    focus_not_modal = False
    elem = webdriver_instance.switch_to.active_element
    parent = elem
    while parent.tag_name != 'body':
        parent = elem.find_element_by_xpath('..')
        if parent:
            if parent == elem:
                focus_not_modal = True
        else:
            break
    return focus_not_modal


def focused_element_visually_in_modal(webdriver_instance, modal):
    in_modal = False
    element = webdriver_instance.switch_to.active_element
    modal_y_bottom = modal.location['y'] + modal.size['height']
    modal_x_right = modal.location['x'] + modal.size['width']
    if (element.location['x'] >= modal.location['x'] and element.location['y'] >= modal.location['y']):
        if (element.location['x'] + element.size['width'] <= modal_x_right):
            if (element.location['y'] + element.size['height'] <= modal_y_bottom):
                in_modal = True
    return in_modal
