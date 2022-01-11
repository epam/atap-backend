from selenium import webdriver
from urllib.parse import urlparse
import re
from framework.element_locator import ElementLocator
from framework.element import Element


name = "!!!test"

locator_required_elements = []
framework_version = 0
WCAG = "4.1.2"
elements_type = "link"
test_data = [
    {
        "page_info": {
            "url": "links/page_fake_links_ok.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links/page_fake_links_fail.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    }
]


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    links = ElementLocator.get_all_of_type(webdriver_instance, ["a"])

    return {
        "status": "PASS",
        "message": "No fake links found",
        "elements": [
            {
                "element": links[0],
                "problem": "Test problem type 1",
                "error_id": "problemtype_11",
                "severity": "WARN"
            },
            {
                "element": links[1],
                "problem": "Test problem type 1",
                "error_id": "problemtype_11",
                "severity": "WARN"
            },
            {
                "element": links[2],
                "problem": "Test problem type 2",
                "error_id": "problemtype_11",
                "severity": "FAIL"
            }

        ],
        "checked_elements": links
    }
