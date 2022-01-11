from selenium import webdriver

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator


name = "Ensures that tables are marked up appropriately"
WCAG = "1.3.1"
depends = ["test_base_tables"]
webdriver_restart_required = False
elements_type = "table"
framework_version = 4
locator_required_elements = ["table"]
test_data = [
    {
        "page_info": {
            "url": "tables/page_good_true_tables.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tables/page_bugs_h51.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


def is_visible(elem: Element, driver: webdriver.Firefox):
    def check_visible(e: Element):
        element = e.get_element(driver)
        return (element and element.size['width'] * element.size['height'] > 0 and element.is_displayed() and
                element.is_enabled())
    return elem.safe_operation_wrapper(check_visible, on_lost=lambda: False)


def wcag(driver: webdriver, table: Element):
    """
        H51: Using table markup to present tabular information
        WSAG: https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/H51
        """
    tags = {'tr', 'th', 'td'}
    child_tags = set(map(lambda x: x.tag_name, table.find_by_xpath(".//*", driver)))
    if not tags <= child_tags:
        return {
            "element": table,
            "problem": "Incorrect table layout",
            "severity": "FAIL" if is_visible(table, driver) else "WARN"
        }


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    bad_elements = []
    print(dependencies)
    if dependencies["test_base_tables"]["status"] != "PASS":
        return dict(status="NOELEMENTS", message="Don't have tables on page",
                    checked_elements=[])
    tables = [elem['table'] for elem in dependencies["test_base_tables"]["tables"]]
    i = 1

    def check_table(table: Element):
        nonlocal i
        print(f'Analyzing {i} table = {table}')
        i += 1
        result = wcag(webdriver_instance, table)
        if result is not None:
            bad_elements.append(result)
    Element.safe_foreach(tables, check_table)
    if bad_elements:
        return dict(status="FAIL", message="Incorrectly designed table", elements=bad_elements,
                    checked_elements=tables)
    return dict(status="PASS", message="The tables complies with the requirements WSAG",
                checked_elements=tables)
