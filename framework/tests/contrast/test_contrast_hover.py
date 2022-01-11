from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.tests.contrast.lib import FramesContrast

name = '''Ensures that contrast ratio for all interactive elements (text and non-text) on hover does not violate requirements (1.4.3, 1.4.11)'''
WCAG = '1.4.3'
framework_version = 5
webdriver_restart_required = False

elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "contrast/page_good_hover.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "contrast/page_bugs_hover.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """
    A search is made for all elements without children. We go through the elements, make HOVER through js and look at
    the background and color through css (if background-color is not in css and background-image is not a gradient,
    then we find all the elements that intersect with the current one and look for them or fill( in case it is canvas),
     or background-color). We calculate the contrast using the formula.
    :param webdriver_instance (webdriver.Firefox):
    :param activity (Activity):
    :param element_locator (ElementLocator):
    :return: result dict
            {
                'status': <'FAIL', 'PASS' or 'NOELEMENTS'>,
                'message': <string>,
                'elements': [
                    {
                        "element": element,
                        "severity": "FAIL",
                        "screenshot": file.name
                    }],
                'checked_elements': [<Element>, ...]
             }
    """
    activity.get(webdriver_instance)
    return FramesContrast(webdriver_instance, element_locator).result(action='hover')
