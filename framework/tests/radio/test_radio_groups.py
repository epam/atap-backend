import time
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from lxml import etree
from framework.element_locator import ElementLocator
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, \
                                       ElementNotVisibleException, ElementClickInterceptedException, \
                                       ElementNotInteractableException, WebDriverException, ElementClickInterceptedException
from framework.element import Element, ElementLostException

name = "Test for elements behaving like radiobuttons"
IGNORED_TAGS = ['script', 'style', 'section', 'br', 'table', 'tr', 'hr', 'a', 'p', 'ul']
possible_radio = []
possible_radiogroup = []
possible_radiogroup_ids = []
webdriver_restart_required = True

WCAG = '2.1.1'
framework_version = 0
elements_type = "radio"
test_data = [
    {
        "page_info": {
            "url": "page_good_radio.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_bugs_radio.html"
        },
        "expected_status": "WARN",
        "expected_problem_count": 1
    }
]

depends = ["test_radio_buttons"]


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    """
    done:
    1) checked labels or internal text
    2) the behavior of lika radiobutton was checked for elements not marked as input: aligned with X,
    changes of one radiobutton entail changes in neighbors (the neighbors were considered buttons 
    of a similar structure and visually aligned).

    Restrictions
    1. If in the process of clicking all the elements the page has changed (there was a transition to a new one,
    an alert or a dialog box appeared), then further testing may break.
    2. It is possible to implement horizontal tabs (menu) with which the signs can match. A further possible solution,
    if necessary, is to search for the visual "circle" pattern at the beginning of the active elements.
    3. If the active element is wrapped in many containers and the visual beacon is made using pseudo-elements and is not present in the DOM

    """
    custom_radio_groups = dependencies["test_radio_buttons"]["radiogroups"]
    custom_groups = list()
    elements = list()

    for radio_group in custom_radio_groups:
        if 'type="radio"' not in radio_group['element'].source:
            custom_groups.append(radio_group['element'])
            if not radio_group['has_correct_navigation']:
                elements.append(
                    {"element": radio_group['element']})

    result = ''
    if len(elements) > 0:
        result = 'Some problems with radiogroups found'
        status = "WARN"
    else:
        result = 'Problems with radiogroups not found'
        status = "PASS"

    return {
        "status": status,
        "message": result,
        "elements": elements,
        "checked_elements": custom_groups
    }


def get_element_as_string(element):
    # get outerHTML of element
    return element.get_attribute('outerHTML')


def element_in_possible_radio(el):
    flag = False
    for btn in possible_radio:
        if outerhtml_elements_are_similar(btn['outerHTML'], get_element_as_string(el)):
            flag = True
    return flag


def outerhtml_elements_are_similar(element1, element2):
    similar = False
    try:
        el_1 = etree.fromstring(element1)
        el_2 = etree.fromstring(element2)
        if el_1.tag == el_2.tag:
            classes_1 = str(el_1.get('class')).split()
            classes_2 = str(el_2.get('class')).split()
            common_classes = list(set(classes_1).intersection(classes_2))
            if len(common_classes) > 0 or (el_1.get('role') == el_2.get('role') and len(el_1.get('role')) > 0) or (el_1.get('name') == el_2.get('name') and len(el_1.get('name')) > 0):
                similar = True
    except:
        pass
    return similar


def test_up_down_btn(webdriver_instance, radio_group):
    # check that radiogroup has correct keyboard control
    navigation_working = True
    all_children = radio_group.find_elements_by_xpath(".//*")
    for child in all_children:
        if not element_in_possible_radio(child):
            all_children.remove(child)
    all_children_framework = [Element(el, webdriver_instance) for el in all_children]
    if all_children:
        try:
            all_children[0].click()
            time.sleep(0.5)
            for i in range(1, len(all_children)):
                elem = webdriver_instance.switch_to.active_element
                elem.send_keys(Keys.DOWN)
                time.sleep(0.2)
                elem = webdriver_instance.switch_to.active_element
                if elem != all_children[i]:
                    navigation_working = False
                    break
            for i in range(len(all_children)-1, 0):
                elem = webdriver_instance.switch_to.active_element
                elem.send_keys(Keys.UP)
                time.sleep(0.2)
                elem = webdriver_instance.switch_to.active_element
                if elem != all_children[i]:
                    navigation_working = False
                    break
        except ElementNotVisibleException:
            pass
    for child in all_children_framework:
        if child.source == '<br>':
            all_children_framework.remove(child)
    return navigation_working, all_children
