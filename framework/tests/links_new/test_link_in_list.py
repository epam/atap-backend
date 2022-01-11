from framework.element import Element
from framework.tests.links_new.lib import check_any_description_of_link_is_missing, text_is_present
from framework.libs.distance_between_elements import distance

framework_version = 5
WCAG = '2.4.4'
name = "Ensures that the links in the lists(native and not native) are correct."
elements_type = "link"
depends = ["test_visible_list", "test_related_elements_as_list"]
webdriver_restart_required = False
test_data = [
    {
        "page_info": {
            "url": "links_new/link-in-list/page_good.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/link-in-list/page_good_2.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/link-in-list/page_good_3.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/link-in-list/page_good_4.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/link-in-list/page_good_5.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/link-in-list/page_bug.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "links_new/link-in-list/page_bug_2.html"
        },
        "expected_status": "FAIL"
    }
]


def check_header_in_native_list(driver, list_elem):
    return text_title_element(driver, list_elem)


def search_for_the_nearest_element(driver, target, options):
    options = list(filter(lambda x: target not in x.find_by_xpath('descendant::*', driver) and x != target, options))
    min_distance = distance(driver, target, options[0])
    nearest = options[0]
    for option in options:
        cur_distance = distance(driver, target, option)
        if cur_distance < min_distance:
            min_distance = cur_distance
            nearest = option
    return nearest


def text_title_element(driver, list_elem: Element):
    parent = list_elem.get_parent(driver)
    children = parent.find_by_xpath('child::*', driver)
    while len(children) < 2 and parent.tag_name != 'body':
        parent = parent.get_parent(driver)
        if parent:
            children = parent.find_by_xpath('child::*', driver)
        else:
            break

    if len(children) < 2:
        return ''

    nearest_element = search_for_the_nearest_element(driver, list_elem, children)
    return text_is_present(nearest_element, driver)


def check_header_in_not_native_list(driver, list_elem):
    return list_elem.header or text_title_element(driver, list_elem.parent)


def test(webdriver_instance, activity, element_locator, dependencies):
    activity.get(webdriver_instance)
    body = element_locator.get_all_of_type(webdriver_instance, element_types=['body'])[0]
    native_lists = element_locator.get_all_of_type(webdriver_instance, element_types=['ul', 'ol'])
    visible_lists = dependencies["test_visible_list"]['visible_lists']
    related_as_lists = dependencies["test_related_elements_as_list"]['related_as_lists']
    result = {'status': "NOELEMENTS",
              'message': 'There are no links for testing.',
              'elements': [],
              'checked_elements': []}
    counter = 1

    def check_native(list_elem):
        nonlocal counter
        links = list_elem.find_by_xpath('descendant::a', webdriver_instance)
        if list_elem.find_by_xpath(f'descendant::{list_elem.tag_name}', webdriver_instance):
            links = list(filter(lambda x: len(x.find_by_xpath(f'ancestor::{list_elem.tag_name}',
                                                              webdriver_instance)) == 1, links))

        result['checked_elements'].extend(links)
        if links and not check_header_in_native_list(webdriver_instance, list_elem):
            for link in links:
                print(f'\rAnalyzing links {counter}/{len(links)}', end="", flush=True)
                counter += 1

                if check_any_description_of_link_is_missing(webdriver_instance, body, link):
                    result["elements"].append(
                        {"element": link,
                         "problem": f"Header not found for non-native list with link, list = {list}",
                         "severity": "FAIL"})

    def check_not_native(list):
        nonlocal counter
        links = list.parent.find_by_xpath('descendant::a', webdriver_instance)
        result['checked_elements'].extend(links)
        if links and not check_header_in_not_native_list(webdriver_instance, list):
            for link in links:
                print(f'\rAnalyzing links {counter}/{len(links)}', end="", flush=True)
                counter += 1

                if check_any_description_of_link_is_missing(webdriver_instance, body, link):
                    result["elements"].append(
                        {"element": link,
                         "problem": f"Header not found for non-native list with link, list = {list}",
                         "severity": "FAIL"})
    if native_lists:
        Element.safe_foreach(native_lists, check_native)

    if visible_lists or related_as_lists:
        Element.safe_foreach(visible_lists + related_as_lists, check_not_native)

    if result['elements']:
        result['status'] = 'FAIL'
        result['message'] = 'The detected errors in the links located in the list.'
    elif result['checked_elements']:
        result['status'] = 'PASS'
        result['message'] = 'All links in the lists are executed correctly!'
    return result

