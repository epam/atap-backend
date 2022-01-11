import itertools


from framework.element import Element
from framework.tests.links_new.lib import text_is_present, check_any_description_of_link_is_missing


framework_version = 5
WCAG = '2.4.4'
name = "Ensures that the links in the tables are correct."
elements_type = "link"
depends = ["test_base_tables", "test_tables_struct"]
webdriver_restart_required = False
test_data = [
    {
        "page_info": {
            "url": "links_new/link-in-table/page_bug.html"
        },
        "expected_status": "FAIL",
    },
    {
        "page_info": {
            "url": "links_new/link-in-table/page_bug_2.html"
        },
        "expected_status": "FAIL",
    },
    {
        "page_info": {
            "url": "links_new/link-in-table/page_bug_3.html"
        },
        "expected_status": "FAIL",
    },
    {
        "page_info": {
            "url": "links_new/link-in-table/page_bug_4.html"
        },
        "expected_status": "FAIL",
    },
    {
        "page_info": {
            "url": "links_new/link-in-table/page_good.html"
        },
        "expected_status": "PASS"
    },
]


def check_headers_in_native_table(driver, table: Element):
    trs = table.find_by_xpath('descendant::tr', driver)
    if len(trs) < 2:
        return False

    horizontal_headers = trs[0].find_by_xpath('descendant::th', driver) if trs else []
    if len(horizontal_headers) < 2 or any([not text_is_present(header, driver) for header in horizontal_headers[1:]]):
        return False

    for tr in trs[1:]:
        vertical_header = tr.find_by_xpath('descendant::th', driver)
        if len(vertical_header) != 1 or not text_is_present(vertical_header[0], driver):
            return False
    return True


def get_descendants(driver, elem: Element):
    descendants = []
    stack = elem.safe_operation_wrapper(lambda e: e.find_by_xpath('child::*', driver), on_lost=lambda: [])
    while stack:
        elem = stack.pop()
        children = elem.safe_operation_wrapper(lambda e: e.find_by_xpath('child::*', driver), on_lost=lambda: [])
        if len(children) < 2:
            descendants.append(elem)
        else:
            stack.extend(children)
    return descendants


def check_headers(driver, table, axis):
    descendants = sorted(get_descendants(driver, table), key=lambda e: e.get_element(driver).location[axis])
    candidates_in_headers = list(next(itertools.groupby(descendants, lambda e: e.get_element(driver).location[axis]))[1])
    for candidate in candidates_in_headers:
        if (not text_is_present(candidate, driver) or
                candidate.safe_operation_wrapper(lambda e: e.find_by_xpath('descendant::a', driver), on_lost=lambda: False)):
            return False
    return True


def check_headers_in_not_native_table(driver, table):
    return check_headers(driver, table, axis='y') and check_headers(driver, table, axis='x')


def test(webdriver_instance, activity, element_locator, dependencies):
    """

    :param webdriver_instance:
    :param activity:
    :param element_locator:
    :param dependencies:
    :return:
    """
    activity.get(webdriver_instance)
    body = element_locator.get_all_of_type(webdriver_instance, element_types=['body'])[0]

    result = {'status': "NOELEMENTS",
              'message': 'There are no links for testing.',
              'elements': [],
              'checked_elements': []}

    counter = 1

    def check_native(table):
        nonlocal counter
        links = table['table'].find_by_xpath('descendant::a', webdriver_instance)
        result['checked_elements'].extend(links)
        if links and not check_headers_in_native_table(webdriver_instance, table['table']):
            for link in links:
                print(f'\rAnalyzing links {counter}/{len(links)}', end="", flush=True)
                counter += 1

                if check_any_description_of_link_is_missing(webdriver_instance, body, link):
                    result["elements"].append(
                        {"element": link,
                         "problem": f"There are no headers for a cell with a link in the native table {table}",
                         "severity": "FAIL"})

    if "tables" in dependencies["test_base_tables"]:
        Element.safe_foreach(dependencies["test_base_tables"]["tables"], check_native)

    def check_not_native(table):
        nonlocal counter
        links = table['element'].find_by_xpath('descendant::a', webdriver_instance)
        result['checked_elements'].extend(links)
        if links and not check_headers_in_not_native_table(webdriver_instance, table['element']):
            for link in links:
                print(f'\rAnalyzing links {counter}/{len(links)}', end="", flush=True)
                counter += 1

                if check_any_description_of_link_is_missing(webdriver_instance, body, link):
                    result["elements"].append(
                        {"element": link,
                         "problem": f"There are no headers for a cell with a link in the non native table {table}",
                         "severity": "FAIL"})

    if "elements" in dependencies["test_tables_struct"]:
        Element.safe_foreach(dependencies["test_tables_struct"]["elements"], check_not_native)

    if result['elements']:
        result['status'] = 'FAIL'
        result['message'] = 'The detected errors in the links located in the table cells.'
    elif result['checked_elements']:
        result['status'] = 'PASS'
        result['message'] = 'All links in the tables are executed correctly!'
    return result
