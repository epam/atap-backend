from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator


name = "Ensures that flickering images on page last not over 5 seconds and can be paused or stopped"
WCAG = "2.2.2"
depends = ["test_base_fl"]

framework_version = 4
webdriver_restart_required = False
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "flicker/page_good_5sec.html"
        },
        "expected_status": "WARN",
        "expected_problem_count": 2
    },
    {
        "page_info": {
            "url": "flicker/page_bad_5sec.html"
        },
        "expected_status": "WARN",
        "expected_problem_count": 2
    }
]


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator, dependencies):
    """..."""
    activity.get(webdriver_instance)
    if dependencies["test_base_fl"]['status'] == "NOELEMENTS":
        return dict(status="NOELEMENTS", message="No elements on page", checked_elements=[])

    checked_elements = [gif["gif"] for gif in dependencies["test_base_fl"]['gifs']]
    result = {
        "status": "WARN",
        "message": "There are gifs which might violate WCAG 2.2.2",
        "checked_elements": checked_elements,
        "elements": list(),
    }

    print("====>Start testing")
    for gif in dependencies["test_base_fl"]['gifs']:
        result["elements"].append({
            "element": gif['gif'],
            "problem": "There is gif which might lasts more than 5 seconds and might not have a stop/pause mechanism",
        })
    return result

