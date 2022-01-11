import statistics
from selenium import webdriver
from typing import List
from re import match
from bs4 import BeautifulSoup

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.list.lib import WebList, is_visible, check_correct_role_for_list, \
    check_correct_role_for_list_items, get_children
from framework.libs.distance_between_elements import distance, intersection


name = "Ensures that related elements are implemented using lists markup"
framework_version = 5
WCAG = '1.3.1'
elements_type = ""
depends = ["test_visible_list"]
webdriver_restart_required = False
EPSILON = 0.33
EPSILON_2 = 0.4

test_data = [
    {
        "page_info": {
            "url": "list/page_good_list_2.html"
        },
        "expected_status": "PASS",
    },
    {
        "page_info": {
            "url": "list/page_bug_list_10.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_false_positive_paragraphs.html"
        },
        "expected_status": "NOELEMENTS"
    }
]


def check_attributes(driver: webdriver.Firefox, elements: List[Element]) -> bool:
    keys = elements[0].get_attributes(driver).keys()
    return len(list(filter(lambda e: not is_visible(driver, e) or e.get_attributes(driver).keys() == keys,
                           elements))) / len(elements) >= 0.75


def check_descendant_tags(driver: webdriver.Firefox, elements: List[Element]) -> bool:
    def get_descendants(elem: Element):
        return elem.find_by_xpath('descendant-or-self::*', driver)

    def get_descendants_tags(elem: Element):
        return [d.tag_name for d in get_descendants(elem)]

    sample_tags = get_descendants_tags(elements[0])
    sample_tags.sort()

    def check_text_size(elems):
        def get_row_height(e):
            css = [e.get_element(driver).value_of_css_property(n) for n in ["line-height", "font-size"]]
            height = None
            for c in css:
                height = int(match(r'\d+', c).group(0)) if match(r'\d+', c) and height is None else height
            return height

        def check_number_of_rows(e):
            height = get_row_height(e)
            return height is None or height == 0 or e.get_element(driver).size['height'] / height < 3
        return elems and all(elem.get_text(driver) and check_number_of_rows(elem) for elem in elems)

    def check(elem: Element):
        def compare_tags(tags):
            return sum(e1 == e2 for e1, e2 in zip(sample_tags, tags)) / max(len(sample_tags), len(tags)) > 0.9

        def get_children_with_text(e):
            return [e for e in get_children(driver, e) if e.get_text(driver).strip()]

        descendants = get_descendants(elem)
        return ((not descendants or compare_tags(sorted(d.tag_name for d in descendants)))
                and (not elem.get_text(driver) or check_text_size(list(filter(
                   lambda e: e.get_text(driver) and not get_children_with_text(e), descendants)))))
    return sum(check(e) for e in elements) / len(elements) >= 0.7 and (any([elem.tag_name != 'button' for elem in elements]) or len(elements) > 2)


def compare_size_with_window(driver, web_list: WebList) -> bool:
    size = web_list.parent.get_element(driver).size
    elements = [e.get_element(driver) for e in web_list.elements]
    if web_list.axis == 'x':
        real_height = sum([e.size['height'] for e in elements])
        real_width = max([e.size['width'] for e in elements])
    else:
        real_height = max([e.size['height'] for e in elements])
        real_width = sum([e.size['width'] for e in elements])
    window_size = driver.get_window_size()
    return (min(size['height'], real_height) < window_size['height'] - 15
            and min(size['width'], real_width) / window_size['width'] <= 0.85)


def compare_sizes(driver: webdriver.Firefox, elements: List[Element]):
    web_elements = [elem.get_element(driver) for elem in elements]
    height_median = statistics.median([elem.size['height'] for elem in web_elements])
    width_median = statistics.median([elem.size['width'] for elem in web_elements])
    epsilon = EPSILON if len(web_elements) < 3 else EPSILON_2
    return sum(abs(elem.size['height'] - height_median) / height_median < epsilon
               and abs(elem.size['width'] - width_median) / width_median < epsilon
               and elem.size['height'] / elem.size['width'] <= 1.9 for elem in web_elements) / len(web_elements) > 0.66


def check_location(driver: webdriver.Firefox, list_: WebList):
    sorted_coord = 'y' if list_.axis == 'x' else 'x'
    elements = sorted(list_.elements, key=lambda e: e.get_element(driver).location[sorted_coord])
    for el1, el2 in zip(elements, elements[1:]):
        elem1 = el1.get_element(driver)
        elem2 = el2.get_element(driver)
        if abs(elem1.location['y'] - elem2.location['y']) < 1 and abs(elem1.location['x'] - elem2.location['x']) < 1:
            return False
    return True


def is_empty(driver, element: Element):
    return not element.find_by_xpath('child::*', driver) and not element.get_text(driver)


def check_empty_items(driver: webdriver.Firefox, elements: List[Element]):
    return sum([not is_empty(driver, elem) for elem in elements]) / len(elements) > 0.5


def filter_visible_elements(driver, list_: WebList):
    list_.elements = list(filter(lambda e: is_visible(driver, e), list_.elements))
    return len(list_.elements) > 1


def check_intersection(driver: webdriver.Firefox, elements: List[Element]):
    return all([not elem1.find_by_xpath('child::img', driver) or not elem2.find_by_xpath('child::img', driver)
                or not intersection(driver, elem1.find_by_xpath('child::img', driver)[0], elem2.find_by_xpath('child::img',driver)[0])
                for (elem1, elem2) in zip(elements, elements[1:])])


def check_text(driver: webdriver.Firefox, list_: WebList):
    def get_text(x: Element):
        return x.get_text(driver).strip() or BeautifulSoup(x.source, 'lxml').get_text().strip()
    elements_with_text = [get_text(x) for x in list_.elements if get_text(x)]
    return len(elements_with_text) / len(list_.elements) > 0.5 or not elements_with_text


def check_images(driver: webdriver.Firefox, list_: WebList):
    return all(len(x.find_by_xpath('descendant-or-self::img', driver)) == 1 for x in list_.elements)


def check_advertisement(driver: webdriver.Firefox, list_: WebList):
    return not list_.parent.find_by_xpath('descendant-or-self::rg-adfox', driver)


def identify_related_elements(driver: webdriver.Firefox, candidates: List[WebList]):
    return list(filter(lambda c: (
            filter_visible_elements(driver, c) and check_advertisement(driver, c) and check_text(driver, c)
            and check_attributes(driver, c.elements) and check_empty_items(driver, c.elements)
            and check_descendant_tags(driver, c.elements) and compare_sizes(driver, c.elements)
            and compare_size_with_window(driver, c) and (c.header is None or c.header.get_text(driver))
            and check_location(driver, c) and check_intersection(driver, c.elements)), candidates))


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    base_test_result = dependencies["test_visible_list"]
    candidate_lists = base_test_result["candidate_lists"] + base_test_result['horizontal_lists']

    result = {
        'status': "PASS",
        'message': 'All lists are implemented correctly!',
        'elements': [],
        'checked_elements': base_test_result['native_lists'],
        'related_as_lists': []
    }

    lists = identify_related_elements(webdriver_instance, candidate_lists)
    result['related_as_lists'].extend(lists)
    if not lists and not result['checked_elements']:
        result['status'] = 'NOELEMENTS'
        result['message'] = 'The custom implemented lists were not found.'
        print(result)
        return result
    counter = 1

    def check_list(l):
        nonlocal counter
        print(f'\rAnalyzing lists {counter}/{len(lists)}', end="", flush=True)
        counter += 1
        result['checked_elements'].append(l.parent)
        role_list = check_correct_role_for_list(webdriver_instance, l)
        role_listitem = check_correct_role_for_list_items(webdriver_instance, l)
        if not role_list or not role_listitem:
            result["elements"].append({"element": l.parent,
                                       "problem": "Non-native element, grouped as list, but without a role='list'",
                                       "severity": "FAIL"})
    Element.safe_foreach(lists, check_list)
    if result["elements"]:
        result["status"] = "FAIL"
        result['message'] = 'Non-native elements were found, grouped as lists, but without a role="list".'
    print(result)
    return result
