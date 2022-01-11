import time

from selenium import webdriver

from framework.element_locator import ElementLocator

framework_version = 4
elements_type = 'modal windows'
WCAG = "2.4.6"
TITLE_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

name = "Test for check modal window title"
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
        "expected_status": "WARN",
        "expected_problem_count": 1
    }
]

def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    elements = []
    result = 'Problems with modal dialog not found'
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
            if not modal_has_title(modal.get_element(webdriver_instance)):
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
        result = "Modal dialog hasn't title"
        status = 'WARN'

    if len(activators) == '0':
        status = "NOELEMENTS"

    return {
        "status": status,
        "message": result,
        "elements": elements,
        "checked_elements": activators,
    }


def modal_has_title(modal):
    has_title = False
    children = modal.find_elements_by_xpath(".//*")
    if len(children) > 0:
        child = children[0]
        if child.tag_name in TITLE_TAGS:
            has_title = True
    return has_title
