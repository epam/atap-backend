import time
from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.list.lib import get_children

test_data = [
    {
        "page_info": {
            "url": "list/page_good_list.html"
        },
        "expected_status": "PASS",
    },
    {
        "page_info": {
            "url": "list/page_good_list_3.html"
        },
        "expected_status": "PASS",
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
            "url": "list/page_bug_list_role.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 3
        }
    }
]

name = "Ensure that if you use role=list, you must have children with role=listitem."
webdriver_restart_required = False
framework_version = 5
WCAG = '4.1.2'
elements_type = ""


def role_children(driver, elem: Element):
    def check(el: Element):
        role = el.get_attribute(driver, 'role')
        return role == 'listitem' or (role == 'group' and all(e.get_attribute(driver, 'role') == 'listitem'
                                                              for e in get_children(driver, el)))

    return all(check(e) for e in get_children(driver, elem))


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    elements_with_role_list = element_locator.get_all_by_xpath(webdriver_instance, "//*[@role='list']")
    elements_with_role_listitem = element_locator.get_all_by_xpath(webdriver_instance, "//*[@role='listitem']")

    if not elements_with_role_list and not elements_with_role_listitem:
        return {
            'status': "NOELEMENTS",
            'message': 'The elements with role="list" were not found.',
            'elements': [],
            'checked_elements': []
        }

    result = {
        'status': "PASS",
        'message': 'All lists are implemented correctly!',
        'elements': [],
        'checked_elements': elements_with_role_list + elements_with_role_listitem
    }

    def check_list(e: Element):
        if not role_children(webdriver_instance, e):
            result["elements"].append({"element": e,
                                       "problem": "The technique was not performed: if role=list is used, then he must "
                                                  "have had a child with role=listitem or role=group and already has a "
                                                  "role=listitem.",
                                       "error_id": 'RoleList',
                                       "severity": "FAIL"})

    def check_listitem(e: Element):
        if all(el.get_attribute(webdriver_instance, 'role') != 'list' for el in e.find_by_xpath("ancestor::*", webdriver_instance)):
            result["elements"].append({"element": e,
                                       "problem": "The technique was not executed: an element with role=listitem must "
                                                  "have had an ancestor with role=list.",
                                       "error_id": 'RoleList',
                                       "severity": "FAIL"})

    start = time.time()
    Element.safe_foreach(elements_with_role_list, check_list)
    Element.safe_foreach(elements_with_role_listitem, check_listitem)
    print(f"time to check role of elements = {time.time() - start}")
    if result["elements"]:
        result["status"] = "FAIL"
        result['message'] = 'Elements with an invalid role were found!'
    return result
