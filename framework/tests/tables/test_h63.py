from typing import List

from selenium import webdriver

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator


name = "Ensures <td>, <th> elements have attribute scope"
WCAG = "1.3.1"
depends = ["test_base_tables"]
webdriver_restart_required = False
framework_version = 4

elements_type = "table"
test_data = [
    {
        "page_info": {
            "url": "tables/page_good_true_tables.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tables/page_bugs_true_tables.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 3
    }
]


def search_scope(elements: List[Element], driver):
    bad = []
    for el in elements:
        scope = el.get_attribute(driver, "scope")
        headers = el.get_attribute(driver, "headers")
        id = el.get_attribute(driver, "id")
        if scope is None and (id is None or headers is None):
            bad.append({
                "element": el,
                "problem": f"<{el.tag_name}> doesn't has attribute scope"
            })
        elif scope is not None and scope not in ["row", "col", "rowgroup", "colgroup"]:
            bad.append({
                "element": el,
                "problem": f"<{el.tag_name}> has an incorrectly filled attribute scope"
            })
    return bad


def wcag(driver, table: Element):
    """
    1 . <th> have attr scope
    2 . <td> have attr scope if not <th> in table
    3 . scope is in [row, col, rowgroup, colgroup]
    """
    bad_elems = []
    elements = table.find_by_xpath(".//th", driver)
    if not elements:
        elements = table.find_by_xpath(".//td[@class='th']", driver)
        bad_elems.extend(search_scope(elements, driver))
    else:
        bad_elems.extend(search_scope(elements, driver))
    return bad_elems


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    bad_elements = []
    if dependencies["test_base_tables"]["status"] != "PASS":
        return dict(status="NOELEMENTS", message="Don't have tables on page", checked_elements=[])
    tables = [elem['table'] for elem in dependencies["test_base_tables"]['tables']]
    for table in tables:
        bad_elements.extend(wcag(webdriver_instance, table))
    if bad_elements:
        return dict(status="FAIL", message="Incorrectly designed table", elements=bad_elements,
                    checked_elements=tables)
    return dict(status="PASS", message="The tables complies with the requirements WSAG",
                checked_elements=tables)
