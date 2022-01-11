from typing import List
import time

from selenium import webdriver

from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.hide_cookie_popup import hide_cookie_popup
from framework.libs.advanced_click import advanced_link_click

'''
TODO: 
every tab with role = ”tab” has an aria-controls = ”...” attribute. If the attribute is absent - bug 4.1.2. 
The validity of the attribute is checked by ahe.

Each tab must have the aria-selected attribute specified. The selected tab has aria-selected = ”true”, all others have aria-selected = ”false”:

If the attribute is missing or takes an incorrect value for the active tab - bug 4.1.2.

If the aria-selected = "false" attribute is absent for the currently inactive tabs - then bug 4.1.2, BP

If the aria-selected = "true" attribute is specified for the currently inactive tabs - bug 4.1.2

If a tab has a dropdown menu, then it should be implemented as a menu button and verified by a test on the menu. 
(example: the View tab in the tabpanel https://www.zkoss.org/zkdemo/combobox/simple_combobox;jsessionid=0D428DAFB74678D0416377722BB6548D)

If the tablist is located vertically, then it must have the aria-orientation = ”vertical” attribute. 
If the attribute is missing - bug 4.1.2, BP

If the widget does not have any of the roles or all roles at once and / or does not have the necessary attributes (one or more) 
+ there is no tab-index for the tabs, then - bug 2.1.1 and 4.1.2

If the widget does not have any of the roles or all roles at once and does not have the necessary attributes (one or more), 
but there is a tab index for the tabs, then - bug 4.1.2
'''


depends = ["test_tabs_role"]
webdriver_restart_required = True
name = "Test for checking attributes of tabs"

IGNORED_TAGS = ['script', 'style', 'section', 'br']
WCAG = '4.1.2'
framework_version = 4
elements_type = "tabpanel"
test_data = [
    {
        "page_info": {
            "url": "tabs/page_good_tabs.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tabs/page_bugs_tabs.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 5
    },
    {
        "page_info": {
            "url": "tabs/page_bugs_tabs_vertical.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    },
    {
        "page_info": {
            "url": "tabs/page_good_tabs_vertical.html"
        },
        "expected_status": "PASS"
    }
]


def find_vertical_tab_groups(driver: webdriver.Firefox, tab_groups):
    vertical_tab_lists = []
    for parent, tabs in tab_groups.items():
        if len(tabs) > 1 and abs(tabs[0].get_element(driver).location['x'] - tabs[1].get_element(driver).location['x']) <= 2:
            vertical_tab_lists.append(parent)
    return vertical_tab_lists


def check_aria_selected(driver: webdriver.Firefox, result: dict, tabs: List[Element]):
    res = False
    for tab in tabs:
        advanced_link_click(tab, driver)
        time.sleep(2)
        if 'aria-selected="true"' not in tab.get_element(driver).get_attribute('outerHTML'):
            result['elements'].append({'element': tab, 'error_id': 'ActiveTabAriaSelectedAttr', 'problem': ""})
            res = True

        for t in tabs:
            if t == tab:
                continue
            source = t.get_element(driver).get_attribute('outerHTML')
            if 'aria-selected' not in source:
                result['elements'].append({'element': t, 'error_id': 'InactiveTabAriaSelectedAttrBP', 'problem': ""})
                res = True
            elif 'aria-selected="true"' in source:
                result['elements'].append({'element': t, 'error_id': 'InactiveTabAriaSelectedAttr', 'problem': ""})
                res = True
    return res


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    hide_cookie_popup(webdriver_instance, activity)
    time.sleep(5)

    tab_groups = dependencies["test_tabs_role"]["tab_groups"]
    elements_without_role = dependencies["test_tabs_role"]["elements_without_role"]
    elements_without_tab_index = dependencies["test_tabs_role"]["elements_without_tab_index"]
    elements_with_role_tab = element_locator.get_all_by_xpath(webdriver_instance, "//body//*[@role='tab']")
    result = {'status': 'PASS', 'message': 'Problems with tabs not found', 'elements': [],
              'checked_elements': elements_with_role_tab + list(tab_groups.keys()) + sum(list(tab_groups.values()), [])}
    elements_without_attr = set()

    def check_aria_controls(element: Element):
        if 'aria-controls' not in element.source:
            result['elements'].append({
                'element': element, 'error_id': 'TabControlAttr',
                'problem': "Navigating on tabs should be carried out with the aid of the arrows or TAB "
            })
        elements_without_attr.add(element.get_parent(webdriver_instance))
    Element.safe_foreach(elements_with_role_tab, check_aria_controls)

    for parent, tabs in tab_groups.items():
        if check_aria_selected(webdriver_instance, result, tabs):
            elements_without_attr.add(parent)

    def check_aria_orientation_vertical(tab_list: Element):
        if 'aria-orientation="vertical"' not in tab_list.source:
            result['elements'].append(dict(element=tab_list, error_id='TabAriaOrientationVerticalAttr', problem=""))
            elements_without_attr.add(tab_list)
    Element.safe_foreach(find_vertical_tab_groups(webdriver_instance, tab_groups), check_aria_orientation_vertical)

    for element in elements_without_attr | elements_without_role:
        if element in elements_without_tab_index:
            result['elements'].append(dict(element=element, error_id='WithoutRoleOrAttrWithoutTabIndex', problem=""))
        else:
            if element in elements_without_tab_index:
                result['elements'].append(dict(element=element, error_id='WithoutRoleOrAttrWithTabIndex', problem=""))
    if result['elements']:
        result['message'] = 'Some problems with tabs found'
        result['status'] = 'FAIL'
    print(result)
    for i, r in enumerate(result['elements']):
        print(i + 1, r)
        print(r['element'].source[:500])
        print('----------------------------------------------------------------------------------------------------')
    return result
