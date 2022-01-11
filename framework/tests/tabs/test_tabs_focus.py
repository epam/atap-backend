import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from framework.element_locator import ElementLocator
from framework.libs.hide_cookie_popup import hide_cookie_popup
from framework.tests.tabs.lib import get_common_ancestor

'''


TODO:
You need to go through the tabs and check that the tabs are activated either automatically 
or by pressing Enter / Space. If it doesn't work - bug 2.1.1

Check that elements that act as a tabpanel (with or without role = ”tabpanel”) in the DOM are located 
immediately after the element that combines all tabs (with or without role = ”tablist”). In this case, 
elements that act as a tabpanel (with or without role = ”tabpanel”) can be wrapped in a general <div> 
(example: https://a11y-style-guide.com/style-guide/section-structure.html# kssref-structure-tabs):

If elements that act as a tabpanel (with or without role = ”tabpanel”) are NOT immediately after 
the table and there are no interactive elements - then bug 1.3.2.

If the elements that act as a tabpanel (with or without role = ”tabpanel”) are NOT immediately after 
the table and they have interactive elements - then a bug 2.4.3.

If one tab panel has interactive elements, and the other has bugs 1.3.2 and 2.4.3
'''

depends = ["test_tabs_role"]
webdriver_restart_required = True
name = "Test for checking navagation by tabs"

IGNORED_TAGS = ['script', 'style', 'section', 'br']
WCAG = '2.1.1'
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
            "url": "tabs/page_good_tabs_focus.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tabs/page_bugs_tabs_focus.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]

INTERACTIVE_TAGS = ['button', 'a']


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    hide_cookie_popup(webdriver_instance, activity)
    result = {'status': 'PASS', 'message': 'Problems with tabs not found', 'elements': [], 'checked_elements': []}
    tab_groups = dependencies["test_tabs_role"]["tab_groups"]
    tab_panels = dependencies["test_tabs_role"]["tab_panels"]
    
    for parent, tabs in tab_groups.items():
        if len(tabs) > 1:
            if ((not check_tabs_controls(tabs, webdriver_instance)
                 and not tabs_available_for_tab_navigation(tabs, webdriver_instance))):
                for tab in tabs:
                    result['elements'].append({
                        'element': tab,
                        'problem': "Navigating on tabs should be carried out with the aid of the arrows or TAB ",
                        'error_id': 'tabsFocus'
                    })
        result['checked_elements'].append(parent)
        result['checked_elements'].extend(tabs)

        if parent in tab_panels and tab_panels[parent]:
            common_ancestor = get_common_ancestor(webdriver_instance, parent, tab_panels[parent][0])
            children = common_ancestor.find_by_xpath('child::*', webdriver_instance)
            for elem1, elem2 in zip(children, children[1:]):
                if elem1 == parent and elem2 not in tab_panels[parent] and elem2 != tab_panels[parent][0].get_parent(webdriver_instance):
                    panels = tab_panels[parent]
                    counter = sum([1 if any([e.tag_name in INTERACTIVE_TAGS for e in panel.find_by_xpath("descendant::*", webdriver_instance)]) else 0 for panel in panels])
                    error_id = 'InteractiveAbsentTabsNavigation' if counter == 0\
                        else ('AllInteractiveTabsNavigation' if counter == len(panels) else 'TabsNavigation')
                    result['elements'].append({
                        'element': common_ancestor,
                        'error_id': error_id,
                        'problem': 'Check that the elements that serve as a tab panel (with or without role=”tabpanel”)'
                                   ' in the DOM are located immediately after the element that combines all the tabs '
                                   '(with or without role= " tablist”)'
                    })
                    break

    if result['elements']:
        result['message'] = 'Some problems with tabs found'
        result['status'] = 'FAIL'
    print(result)
    for i, r in enumerate(result['elements']):
        print(i + 1, r)
        print(r['element'].source[:500])
        print('----------------------------------------------------------------------------------------------------')
    return result


def tabs_available_for_tab_navigation(tabs, webdriver_instance):
    if not tabs:
        return False
    elif tabs[-1]:
        tabindex_0 = tabs[0].get_attribute(webdriver_instance, 'tabindex')
        tabindex_1 = tabs[-1].get_attribute(webdriver_instance, 'tabindex')
        if tabindex_0 and tabindex_1:
            if int(tabindex_0) < int(tabindex_1):
                return False
    return True


def check_tabs_controls(tabs, webdriver_instance):
    navigation_working = True
    if tabs:
        if len(tabs) > 1:
            tabs[-1].click(webdriver_instance)
            elem = webdriver_instance.switch_to.active_element
            elem.send_keys(Keys.RIGHT)
            time.sleep(0.5)
            elem = webdriver_instance.switch_to.active_element
            if elem != tabs[0].get_element(webdriver_instance):
                navigation_working = False
            elem.send_keys(Keys.LEFT)
            time.sleep(0.5)
            elem = webdriver_instance.switch_to.active_element
            if elem != tabs[-2].get_element(webdriver_instance):
                navigation_working = False
    return navigation_working
