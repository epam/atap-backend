from selenium import webdriver
from framework.element_locator import ElementLocator
import time
from framework.element import Element

from framework.tests.modal.common_modal import ModalFinder

'''
This test is developed to detect modal windows on a page (in its
particular state)
Detects backdrop and the window itself, checks for certain roles, returns a
list of items.

To do this, send an element to a function 'check_that_element_has_modal' from
common_modal with get a list of modal.

'''


name = "Test for elements behaving like modal"
WCAG = "4.1.2"
framework_version = 4
elements_type = 'modal windows'
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


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    modal_finder = ModalFinder(webdriver_instance, element_locator, activity)
    modal_activators = modal_finder.get_all_activators()
    result = {
        "status": 'PASS',
        "message": 'Problems with modal dialog not found',
        "elements": [],
        "activators": modal_activators,
        "modals": modal_finder.modals,
        "checked_elements": modal_activators
    }

    def check(activator: Element):
        modals = modal_finder.modals[activator]
        if modals:
            modal = modals[0]
            parent = modal.safe_operation_wrapper(lambda e: e.find_by_xpath('parent::div', webdriver_instance),
                                                  on_lost=lambda: None)
            elements = [modal] + (parent if parent is not None and parent and len(parent[0].find_by_xpath(
                'child::*', webdriver_instance)) == 1 else [])
            if all('role="dialog"' not in e.source and 'role="alertdialog"' not in e.source for e in elements):
                result['elements'].append({
                    "element": modal, 
                    "severity": 'FAIL',
                    "interaction_sequence": [{
                        "element": activator,
                        "action": "click"
                    }],
                    "problem": "Modal window does not have role."
                })
            if all('aria-modal="true"' not in e.source for e in elements):
                result['elements'].append({
                    "element": modal, 
                    "severity": 'FAIL',
                    "interaction_sequence": [{
                        "element": activator,
                        "action": "click"
                    }],
                    "problem": "Modal window does not have aria-modal attribute.",
                    "error_id": "AriaModal"
                })
            if all('aria-label' not in e.source and 'aria-labelledby' not in e.source for e in elements):
                result['elements'].append({
                    "element": modal,
                    "severity": 'FAIL',
                    "interaction_sequence": [{
                        "element": activator,
                        "action": "click"
                    }],
                    "problem": "Modal window does not have aria-modal attribute.",
                    "error_id": "AriaLabel"
                })
    Element.safe_foreach(list(modal_finder.modals.keys()), check)

    if result['elements']:
        result['message'] = 'Some problems with modal dialog found'
        result['status'] = 'FAIL'
    if not modal_activators:
        result['status'] = "NOELEMENTS"
    print(result)
    return result


def modal_has_attributes(element):
    return 'role="dialog"' in element.source or 'role="alertdialog"' in element.source, 'aria-modal' in element.source
