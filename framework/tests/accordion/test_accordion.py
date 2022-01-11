from selenium import webdriver
from framework.element import Element, ElementLostException
import time
import re

from framework.element_locator import ElementLocator

from selenium.common.exceptions import ElementNotVisibleException, WebDriverException, StaleElementReferenceException

framework_version = 0

test_data = [
    {
        "page_info": {
            "url": "page_good_accordion.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_bugs_accordion.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 4
    }
]


name = "Test for checking accordions"
#depends = ['test_tabs']
WCAG = '4.1.2'
IGNORED_TAGS = ['script', 'style', 'section', 'br', 'hr', 'svg', 'canvas', 'header', 'input']

elements_type = "accordion"

def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):
    elements = list()
    possible_accordion = list()
    result = 'Problems with accordions not found'
    status = 'PASS'

    activity.get(webdriver_instance)
    # other = dependencies['test_tabs']['tabs']
    other = []
    clickables = element_locator.get_activatable_elements()

    def is_item_of_accordion(element):
        try:
            web_el = element.get_element(webdriver_instance)
            neighbors = get_all_neighbors_without_element(web_el)
            if neighbors:
                neighbors_html_start = get_neighbors_html(neighbors)
                element_height_start = element.get_element(webdriver_instance).size['height']
                element.click(webdriver_instance)
                time.sleep(1)
                neighbors = get_all_neighbors_without_element(element.get_element(webdriver_instance))
                neighbors_html_end = get_neighbors_html(neighbors)
                element_height_end = element.get_element(webdriver_instance).size['height']
                if neighbors_was_changed(neighbors_html_start, neighbors_html_end) and element_height_start != element_height_end:
                    possible_accordion.append(element)
        except (ElementNotVisibleException, WebDriverException, StaleElementReferenceException, ElementLostException):
            pass

    Element.safe_foreach(clickables, is_item_of_accordion)

    if len(possible_accordion) == 0:
        clickables = [el.get_parent(webdriver_instance) for el in clickables]
        Element.safe_foreach(clickables, is_item_of_accordion)

    for accordion in possible_accordion:
        if 'aria-expanded' not in accordion.source or 'aria-controls' not in accordion.source:
            elements.append({"element": accordion, "problem": "Elements with behavior 'like accordion' do not have the necessary roles or attributes. See WCAG 3.1"})

    if len(elements) > 0:
        result = 'Some problems with accordions found'
        status = 'FAIL'

    return {
        "status": status,
        "message": result,
        "elements": elements
    }


def get_neighbors_html(elements):
    neig = []
    for el in elements:
        neig.append(el.get_attribute('outerHTML'))
    return neig


def neighbors_was_changed(elements_html_start, elements_html_end):
    changed = False
    if len(elements_html_start) != len(elements_html_end):
        changed = False
    else:
        for i in range(len(elements_html_start)):
            elements_html_start[i] = re.sub(
                r'\s+', ' ', elements_html_start[i])
            elements_html_end[i] = re.sub(r'\s+', ' ', elements_html_end[i])
            if elements_html_start[i] != elements_html_end[i]:
                changed = True
    return changed


def get_all_neighbors_without_element(element):
    parent = element.find_element_by_xpath('..')
    all_children_by_xpath = parent.find_elements_by_xpath("*")
    all_children_by_xpath.remove(element)

    for child in all_children_by_xpath:
        if element.size['height'] < 10 or element.size['width'] < 20:
            all_children_by_xpath.remove(child)

    for child in all_children_by_xpath:
        if (child.location['x'] != element.location['x']) or (child.location['y'] == element.location['y']):
            all_children_by_xpath.remove(child)

    for child in all_children_by_xpath:
        if (child.tag_name != element.tag_name) or \
             (child.tag_name in IGNORED_TAGS):
            all_children_by_xpath.remove(child)
    return all_children_by_xpath
