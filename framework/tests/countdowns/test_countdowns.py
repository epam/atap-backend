import itertools

from selenium import webdriver

from framework.activity import Activity
from framework.libs.custom_clicker import CustomClicker
from framework.tests.countdowns.testers.by_code import TestByElements
from framework.tests.countdowns.testers.by_opencv import TestByOpenCv
from framework.element_locator import ElementLocator


framework_version = 4
name = "Ensures that for each time limit set by the content, at least one of the 6 points set by the WCAG is true"
WCAG = "2.2.1"
webdriver_restart_required = True

TESTERS = [
    TestByElements,
    TestByOpenCv,
]

_STOP_WORDS = {
    'стоп',
    'сброс',
    'отключение ограничения по времени',
    'reset',
    'stop',
    'avast',
    'disable time limit',
    'остановить',
}

elements_type = "countdown"
test_data = [
    {
        "page_info": {
            "url": "countdowns/page_good_countdown.html"
        },
        "expected_status": "NOELEMENTS"
    },
    {
        "page_info": {
            "url": "countdowns/page_bugs_countdown.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator):
    """
    The main method that determines the behavior of the entire test.

    - He will check the page on 2 tests:
        * First, it's test for changes on page by changes in HTML code.
        * Secondly, it is a test for changes on the page by comparing screenshots of the page.

    - This test according to WCAG 2.2.1

    .. warnings also::
        At the moment, not validated following the requirements of WCAG:
            * Ability to adjust the time limit.
            * The user is warned before time expires and given at least 20 seconds to extend the time limit with
            a simple action (for example, "press the space bar"),
            and the user is allowed to extend the time limit at least ten times.
            * The time limit is longer than 20 hours.

            Because there is no clear design of the countdown in the code
            and in the form of animation (for example: hourglass or analog clock)
    Last update: 01.10.2019
    :param activity:
    :param element_locator:
    :param webdriver_instance: webdriver of browser
    :return: dict with message and elements if have
    """

    def start_testers():
        """Run testers"""
        return list(itertools.chain(*[t.changed(webdriver_instance, element_locator) for t in TESTERS]))

    activity.get(webdriver_instance)
    count = 0
    elements = []
    clicks = []

    while count < 4:
        elements = start_testers().copy()
        if not elements:
            break
        clicks.extend(CustomClicker(element_locator, webdriver_instance, _STOP_WORDS).click())
        count += 1
    if count > 1:
        if clicks:
            elements.extend(clicks)
        return dict(status="FAIL", message="Countdowns doesn't stop, WCAG link: https://clck.ru/H7mDB",
                    elements=elements, checked_elements=[])
    elif count == 1:
        return dict(status="PASS", message="Successfully stopped, WCAG link: https://clck.ru/H7mDB",
                    checked_elements=[])
    return dict(status="NOELEMENTS", message="No elements", checked_elements=[])
