from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.libs.hide_cookie_popup import hide_cookie_popup

webdriver_restart_required = True
name = "Test for checking labels of tabs"

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
            "url": "tabs/page_bugs_tabs_labels.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 4
    }
]


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    hide_cookie_popup(webdriver_instance, activity)
    tab_lists = element_locator.get_all_by_xpath(webdriver_instance, "//body//*[@role='tablist']")
    tab_panels = element_locator.get_all_by_xpath(webdriver_instance, "//body//*[@role='tabpanel']")
    result = {'status': 'PASS', 'message': 'Problems with tabs not found', 'elements': [],
              'checked_elements': tab_lists + tab_panels}

    for tab in tab_lists:
        if 'aria-labelledby' not in tab.source and 'aria-label' not in tab.source:
            result['elements'].append({
                'element': tab, 'error_id': 'TabListLabel',
                'problem': "Navigating on tabs should be carried out with the aid of the arrows or TAB "
            })
    for tab in tab_panels:
        if 'aria-labelledby' not in tab.source:
            result['elements'].append({
                'element': tab, 'error_id': 'TabPanelLabel',
                'problem': "Navigating on tabs should be carried out with the aid of the arrows or TAB "
            })

    if result['elements']:
        result['message'] = 'Some problems with tabs found'
        result['status'] = 'FAIL'

    print(result)
    return result
