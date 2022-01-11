import time
import re
from selenium import webdriver
from typing import List
from bs4 import BeautifulSoup as bs

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.list.lib import WebList, get_children, check_correct_role_for_list, \
    check_correct_role_for_list_items, is_visible
from framework.libs.distance_between_elements import distance


framework_version = 5
WCAG = '1.3.1'
elements_type = ""
depends = ["test_base_list"]
webdriver_restart_required = False

test_data = [
    {
        "page_info": {
            "url": "list/page_good_list.html"
        },
        "expected_status": "PASS",
    },
    {
        "page_info": {
            "url": "list/page_bug_list.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 2
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_2.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 2
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_3.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 2
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_5.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 2
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_role.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_item.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_list_without_tags.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_6.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_7.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_8.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_lonely_list.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "list/page_bug_list_9.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
]
name = "Ensures that elements that look like lists are implemented using lists markup"


def get_pseudo_before_element(driver: webdriver.Firefox, element: Element) -> str:
    elem = element.safe_operation_wrapper(lambda e: e.get_element(driver), on_lost=lambda: None)
    return driver.execute_script("return window.getComputedStyle(arguments[0], ':before')." +
                                 "getPropertyValue('content');", elem) if elem is not None else ""


def next_symbol(symbol: str) -> str:
    """the following symbol in the numbering(e.g. 'a' -> 'b', '1' -> '2'). P.S. for 'z' is not defined"""
    return str(int(symbol) + 1) if symbol.isdigit() else chr(ord(symbol) + 1)


def get_text(driver, elem: Element) -> str:
    text = elem.safe_operation_wrapper(lambda e: e.get_text(driver), on_lost=lambda: "")
    return text if text else bs(elem.source, 'html.parser').get_text().strip()


def check_duplicate_symbol(driver: webdriver.Firefox, web_list: WebList) -> bool:
    """check that the string starts with the same repeated character"""

    symbol = get_text(driver, web_list.elements[0])[0] if web_list.elements and get_text(driver, web_list.elements[0]) \
        else (get_text(driver, web_list.parent)[0] if get_text(driver, web_list.parent) else '')
    if symbol not in ['*', '-', '•']:
        return False
    return all([get_text(driver, elem) and get_text(driver, elem)[0] == symbol for elem in web_list.elements])


def check_numbering(driver, l: WebList) -> bool:
    # check the numbering at the beginning of the items in the proposed list
    if len(l.elements) < 2:
        return False

    match_first = re.compile(f'\\W?[01a]+')
    first_symbol_regex = re.compile(f'\\W?\\w+')

    def sub(s): return re.sub(r'\W', '', s, re.IGNORECASE)

    text = get_text(driver, l.elements[0])
    if match_first.match(text) is not None:
        prev_symbol = sub(match_first.match(text).group(0))
    else:
        return False

    for elem in l.elements[1:]:
        cur_symbol = sub(first_symbol_regex.match(get_text(driver, elem)).group(0)) if \
            first_symbol_regex.match(get_text(driver, elem)) is not None else ''
        cur_symbol = str(int(cur_symbol)) if cur_symbol.isdigit() else cur_symbol
        if cur_symbol and next_symbol(prev_symbol) == cur_symbol:
            prev_symbol = cur_symbol
        else:
            return False
    return True


def get_background(driver: webdriver.Firefox, elem: Element) -> str:
    return elem.safe_operation_wrapper(lambda e: e.get_element(driver).value_of_css_property("background"), lambda: "")


def check_background(driver: webdriver.Firefox, web_list: WebList) -> bool:
    """check that all items in the list have a background character"""

    def background_is_present(elem: Element):
        background = get_background(driver, elem)
        return background and background.split()[4] != 'none'

    web_list.method = 'background'
    if not web_list.elements:
        return background_is_present(web_list.parent)
    return all([background_is_present(e) for e in web_list.elements])


def check_pseudo_before_element(driver: webdriver.Firefox, web_list: WebList) -> bool:
    """
    FIXME
    :param driver:
    :param web_list:
    :return:
    """
    symbol = get_pseudo_before_element(
        driver, web_list.elements[0]) if web_list.elements else get_pseudo_before_element(driver, web_list.parent)
    good_symbols = ['"•"', '""', '""']
    if symbol not in good_symbols or not (get_text(driver, web_list.elements[0]) if web_list.elements else get_text(
            driver, web_list.parent)):
        return False
    web_list.method = 'pseudo before element'
    return all([symbol == get_pseudo_before_element(driver, e) and get_text(driver, e) for e in web_list.elements[1:]])


def check_list_in_paragraph(driver: webdriver.Firefox, elem: Element):
    numeration_regex = re.compile(f'\\W?[\\dab]+')
    duplicate_bullet_regex = re.compile(r'\W?[*\-—•].+')

    def _check_numbering(previous_number, items):
        if previous_number not in ['0', '1', '2']:
            return False
        for item in items:
            if previous_number is not None and re.match(f'\\W?{previous_number}.+', item.strip()) is not None:
                previous_number = next_symbol(previous_number)
            else:
                return False
        return True

    def _check_duplicate_bullet(items):
        return all([duplicate_bullet_regex.match(i.strip()) is not None for i in items]) if items else False

    candidates = []
    children = get_children(driver, elem)
    candidates.append(dict(parent=elem, elements=[s.strip() for s in get_text(driver, elem).split('\n') if s.strip()]))
    if children and (elem.tag_name == 'p' or len(children) == 1):
        for child in children:
            if child.tag_name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                candidates.append(dict(parent=elem, elements=[get_text(driver, child)]))
    results = []
    for candidate in candidates:
        # skip because the first elem may be header
        elements = candidate['elements'][1:] if len(candidate['elements']) > 2 else candidate['elements']
        if not elements or (len(elements) == 1 and all([i.isdigit() for i in elements[0].split()])):
            continue
        if numeration_regex.match(elements[0].strip()) is not None:
            prev_symbol = re.sub(r'\W', '', numeration_regex.match(elements[0].strip()).group(0))
            if not _check_numbering(prev_symbol, elements):
                continue
            method = 'numbering'
        elif duplicate_bullet_regex.match(elements[0].strip()) is not None:
            if not _check_duplicate_bullet(elements[1:]):
                continue
            method = 'duplicate symbol'
        else:
            continue
        results.append(WebList(candidate['parent'], [], axis='x', method=method, lonely=len(elements) < 2))
    return results


def check_visible_items_is_list(driver: webdriver.Firefox, suspect_list: WebList) -> bool:
    return all([is_visible(driver, item) for item in suspect_list.elements])


def check_marker_list(driver: webdriver.Firefox, suspect_list: WebList) -> bool:
    return check_visible_items_is_list(driver, suspect_list) and (check_numbering(driver, suspect_list) or
                                                                  check_duplicate_symbol(driver, suspect_list) or
                                                                  check_background(driver, suspect_list) or
                                                                  check_pseudo_before_element(driver, suspect_list))


def identify_lonely_lists(driver: webdriver.Firefox, candidates: List[WebList]) -> List[WebList]:
    lonely_lists = list(filter(lambda x: check_background(driver, x) or check_pseudo_before_element(driver, x), candidates))
    lonely_lists.extend(sum([check_list_in_paragraph(driver, l.parent) for l in candidates if l not in lonely_lists], []))
    # filter
    descendants = list(map(lambda x: x.source, sum([e.parent.find_by_xpath('descendant::*', driver) for e in lonely_lists], [])))
    return list(filter(lambda x: x.parent.source not in descendants, lonely_lists))


def identify_lists(driver: webdriver.Firefox, candidates: List[WebList]) -> List[WebList]:
    lists = []

    def check(candidate: WebList):
        if check_marker_list(driver, candidate):
            lists.append(candidate)
    Element.safe_foreach(candidates, check)
    return lists


def group_by_lonely_lists(driver: webdriver.Firefox, lonely_lists: List[WebList]):
    if len(lonely_lists) < 2:
        return lonely_lists

    axis = 'y' if all([l.parent.get_element(driver).location['y'] ==
                       lonely_lists[0].parent.get_element(driver).location['y'] for l in lonely_lists[1:]]) else 'x'
    lonely_lists = sorted(lonely_lists, key=lambda i: i.parent.get_element(driver).location['y' if axis == 'x' else 'x'])
    new_groups = []
    for elem in lonely_lists:
        for new_group in new_groups:
            if (distance(driver, elem.parent, new_group[-1].parent) < 310 and abs(elem.parent.get_element(
                    driver).location[axis] - new_group[-1].parent.get_element(driver).location[axis]) < 3 and
                    elem.method == 'numbering'):
                new_group.append(elem)
                break
        else:
            new_groups.append([elem])
    return [group[0] for group in new_groups]


def filter_lists(driver: webdriver.Firefox, lists: List[WebList], lonely_lists: List[WebList]):
    if lonely_lists and lists:
        descendants = list(map(lambda x: x.source, sum([e.parent.find_by_xpath('descendant::*', driver) for e in lists], [])))
        lonely_lists = set(filter(lambda x: x.parent.source not in descendants, lonely_lists))
        lists = list(filter(lambda x: x.parent.source not in descendants, lists))
        descendants = list(map(lambda x: x.source, sum([e.parent.find_by_xpath('descendant-or-self::*', driver) for e in lonely_lists], [])))
        lists = set(filter(lambda x: x.parent.source not in descendants, lists))
        return list(lists), group_by_lonely_lists(driver, list(lonely_lists))
    else:
        return lists, group_by_lonely_lists(driver, lonely_lists)


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator, dependencies):
    """
    :param webdriver_instance (webdriver.Firefox)
    :param activity (Activity)
    :param element_locator (ElementLocator)
    :param dependencies:
    :return: result dict
            {
                'status': <'FAIL', 'PASS' or 'NOELEMENTS'>,
                'message': <string>,
                'elements': [
                    {
                        "element": <Element>,
                        "problem": ...,
                        "severity": "WARN"/"FAIL",

                    }],
                'checked_elements': [<Element>, ...]
             }
    """
    activity.get(webdriver_instance)
    base_test_result = dependencies['test_base_list']
    candidate_lists, lonely_lists = base_test_result['candidate_lists'], base_test_result['lonely_lists']

    result = {
        'status': "PASS",
        'message': 'All lists are implemented correctly!',
        'elements': [],
        'checked_elements': base_test_result['native_lists'],
        'native_lists': base_test_result['native_lists'],
        'candidate_lists': [],
        'horizontal_lists': base_test_result['horizontal_lists'],
        'visible_lists': []
    }

    lists = identify_lists(webdriver_instance, candidate_lists)
    lonely_lists = identify_lonely_lists(webdriver_instance, lonely_lists)
    lists, lonely_lists = filter_lists(webdriver_instance, lists, lonely_lists)
    result['visible_lists'] = lists + lonely_lists
    result['candidate_lists'] = [l for l in candidate_lists if l not in lists]
    if not lists and not lonely_lists and not result['checked_elements']:
        result['status'] = 'NOELEMENTS'
        result['message'] = 'The custom implemented lists were not found.'
        return result
    counter = 1

    def check_list(list_: WebList):
        nonlocal counter
        print(f'\rAnalyzing lists {counter}/{len(lists) + len(lonely_lists)}', end="", flush=True)
        counter += 1
        if list_.parent.find_by_xpath('ancestor::li', webdriver_instance):
            return

        result['checked_elements'].append(list_.parent)
        role_list = check_correct_role_for_list(webdriver_instance, list_)
        role_listitem = check_correct_role_for_list_items(webdriver_instance, list_)
        if not role_list or not role_listitem:
            elem = {"element": list_.parent,
                    "problem": "This list is not to be found in the shortcut is: it does not match the role. ",
                    "severity": 'WARN' if list_.lonely else "FAIL"}
            result["elements"].append(elem)
    Element.safe_foreach(lists, check_list)
    Element.safe_foreach(lonely_lists, check_list)
    if result["elements"]:
        result["status"] = "FAIL"
        result['message'] = 'Detected non-native lists that will not be found by the screen reader.'
    print(result)
    return result
