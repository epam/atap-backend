from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.tests.flickering_objects.base_func import fps, calculation

name = "Ensures that flickering images on page have size not more than 25% off size page"
WCAG = "2.3.1"
depends = ["test_base_fl"]

framework_version = 4
webdriver_restart_required = False
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "flicker/page_good_size.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "flicker/page_bad_size.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 3
    },
]


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator, dependencies):
    """..."""
    activity.get(webdriver_instance)
    if dependencies["test_base_fl"]['status'] == "NOELEMENTS":
        return dict(status="NOELEMENTS", message="No elements on page", checked_elements=[])
    checked_elements = [gif["gif"] for gif in dependencies["test_base_fl"]['gifs']]
    result = {
        "status": "PASS",
        "message": "Images are valid",
        "checked_elements": checked_elements,
        "elements": list(),
    }

    print("====>Start testing")
    big_size_elements = []
    flickering_elements = []
    for gif in dependencies["test_base_fl"]['gifs']:
        element = gif['gif']
        path = gif['path']
        window_diag = (webdriver_instance.get_window_rect()["height"] ** 2 +
                       webdriver_instance.get_window_rect()["width"] ** 2) ** .5
        element_diag = (element.get_element(webdriver_instance).size['height'] ** 2 +
                        element.get_element(webdriver_instance).size['width'] ** 2) ** .5
        if fps(path) > 3.0:
            flickering_elements.append(element)
            if calculation(window_diag, element_diag, 30.0):
                big_size_elements.append({
                    "element": element,
                    "problem": "Size which more than 25% off size page"
                })

    if big_size_elements:
        result["status"] = "FAIL"
        result["message"] = "There are multiple flickering areas or some elements have size more than 25% off page size"
        for element in big_size_elements:
            result["elements"].append({
                "element": element,
                "problem": "There is an element with size more than 25% off page size",
                "error_id": "FlickeringSize"
            })

    # 2.3.1 G176
    if len(flickering_elements) > 1:
        result["status"] = "FAIL"
        result["message"] = "There are multiple flickering areas or some elements have size more than 25% off page size"
        for element in flickering_elements:
            result["elements"].append({
                "element": element,
                "problem": "There is an flickering area",
                "error_id": "FlickeringArea"
            })

    return result
