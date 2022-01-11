from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.tests.flickering_objects.base_func import fps, path_frames_sec, black2white, calculation
from framework.await_page_load import *

name = "Ensures that flickering images on page have no more than 3 frames per second " \
       "and don't flickering if all the same fps more than 3"
WCAG = "2.3.1"
depends = ["test_base_fl"]

framework_version = 4
webdriver_restart_required = False
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "flicker/page_good_flickering_gifs.html"
        },
        "expected_status": "PASS",
    },
    {
        "page_info": {
            "url": "flicker/page_bad_flickering_gifs.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    },
]


def threshold(path):
    path1, path2 = path_frames_sec(path)
    b1, w1, p1 = black2white(path1)
    b2, w2, p2 = black2white(path2)
    return calculation(b1, b2, 20.0) and calculation(w1, w2, 20.0)


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator, dependencies):
    """"""
    activity.get(webdriver_instance)
    wait_for_page_load(webdriver_instance)
    if dependencies["test_base_fl"]['status'] == "NOELEMENTS":
        return dict(status="NOELEMENTS", message="No elements on page", checked_elements=[])
    checked_elements = [gif["gif"] for gif in dependencies["test_base_fl"]['gifs']]

    bad_elements = []
    for gif in dependencies["test_base_fl"]['gifs']:
        element = gif['gif']
        path = gif['path']
        if fps(path) > 3.0:
            if threshold(path):
                bad_elements.append({
                    "element": element,
                    "problem": "Image has too much dark/white difference in any one second"
                })
            else:
                bad_elements.append({
                    "element": element,
                    "problem": "Image flash more than three times in any one second"
                })
    if bad_elements:
        return dict(status="FAIL", message="Images on this page fail by the criteria of WCAG", elements=bad_elements,
                    checked_elements=checked_elements)
    return dict(status="PASS", message="Images on this page pass by the criteria of WCAG",
                checked_elements=checked_elements)
