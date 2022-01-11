import time

from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.keys import Keys

from framework.element_locator import ElementLocator

framework_version = 4
elements_type = 'modal windows'
WCAG = '2.1.2'

depends = ["test_disguised_modal"]
webdriver_restart_required = True
name = "Test for closing modal window by escape"

'''
This test is developed to detect modal windows on a page (in its particular state).
In the "default" mode it works only if the modal window is open immediately.
This test checking that it possible to close custom modal window by escape

'''

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
        "expected_status": "WARN",
        "expected_problem_count": 1
    }
]


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    elements = []
    result = 'Problems with modal closing not found'
    status = 'PASS'
    activity.get(webdriver_instance)
    activators = dependencies["test_disguised_modal"]["activators"]
    activators_and_modals = dependencies["test_disguised_modal"]["modals"]
    for activator in activators:
        # element_locator.activate_element(activator)
        activator.click(webdriver_instance)
        time.sleep(0.5)
        modals = activators_and_modals[activator]
        if modals:
            modal = modals[0]
            if not modal_is_closing_by_esc(modal, webdriver_instance):
                element = {
                    "element": modal,
                    "severity": 'WARN',
                    "interaction_sequence": [{
                        "element": activator,
                        "action": "click"
                    }],
                }
                elements.append(element)

    if len(elements) > 0:
        result = 'Some problems with modal closing dialog found'
        status = 'WARN'

    if len(activators) == '0':
        status = "NOELEMENTS"

    return {
        "status": status,
        "message": result,
        "elements": elements,
        "checked_elements": activators,
    }


def modal_is_closing_by_esc(modal, webdriver_instance) -> bool:
    body = webdriver_instance.find_element_by_xpath('//body')
    try:
        body.send_keys(Keys.ESCAPE)
        time.sleep(1)
    except ElementNotInteractableException:
        pass
    if modal.get_element(webdriver_instance).size['height'] == 0:
        return True
    return False
