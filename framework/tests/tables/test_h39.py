from selenium import webdriver

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.tests.tables.test_h73 import describes_table

name = "Ensures <table> elements have attribute caption and that the content of the element identifies the table"
WCAG = "1.3.1"
depends = ["spacy_en_lg", "test_base_tables", "test_h73"]
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
        "expected_problem_count": 2
    },
    {
        "page_info": {
            "url": "tables/page_bugs_true_tables_2.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


def wcag(driver, table: Element, model_wrapper):
    bad_elems = []
    """
    H39: Using caption elements to associate data table captions with data tables
    WSAG: https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/H39.html
    """
    summary = table.get_attribute(driver, "summary")
    captions = table.find_by_xpath(".//caption[text()]", driver)
    if not captions:
        bad_elems.append({
            "element": table,
            "problem": "The table is missing <caption>."
        })

    for caption in captions:
        if caption:
            bad_elems.extend(describes_table(driver, table, caption.get_text(driver), model_wrapper))
            if summary:
                if summary == caption.get_text(driver):
                    bad_elems.append({
                        "element": caption,
                        "problem": "The summary attribute should't duplicate caption information"
                    })
                else:
                    bad_elems.extend(describes_table(driver, table, summary, model_wrapper))
            else:
                bad_elems.extend(describes_table(driver, table, caption.get_text(driver), model_wrapper))
        else:
            if not summary:
                bad_elems.append({
                    "element": table,
                    "problem": "Table don't have summary and caption attribute"
                })
            else:
                bad_elems.extend(describes_table(driver, table, summary, model_wrapper))
    return bad_elems


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    bad_elements = []
    checked_elements = []
    print(dependencies)
    if dependencies["test_h73"]["status"] == "NOELEMENTS" or dependencies["test_base_tables"]["status"] != "PASS":
        return dict(status="NOELEMENTS", message="No elements", checked_elements=checked_elements)
    model_wrapper = dependencies["spacy_en_lg"]
    tables = [elem['table'] for elem in dependencies["test_base_tables"]['tables']]
    h_73 = [elem['caption'] for elem in dependencies["test_h73"]['captions']]
    checked_elements.extend(tables+h_73)
    for table in tables:
        bad_elements.extend(wcag(webdriver_instance, table, model_wrapper))
    if bad_elements:
        return dict(status="FAIL", message="Incorrectly designed table", elements=bad_elements,
                    checked_elements=checked_elements)
    return dict(status="PASS", message="The tables complies with the requirements WSAG",
                checked_elements=checked_elements)
