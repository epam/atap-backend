from selenium import webdriver

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.compare_texts import compare_words
from framework.libs.custom_nlp import re_keywords
from framework.libs.stop_words import cached_stopwords


name = "Ensures <table> elements have attribute summary attribute describes " \
       "the table's organization or explains how to use the table"
WCAG = "1.3.1"
depends = ["spacy_en_lg", "test_base_tables"]
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
    }
]
LIMIT = 1.85


def describes_table(driver, table: Element, descriptive_element: str, model_wrapper):
    bad_elem = []
    keys_text = set(descriptive_element.split())
    keys_elements = set()
    for el in table.find_by_xpath(".//*[td or th or tr]", driver):
        keys_elements.update(set(el.get_text(driver).split()))

    stop_words = cached_stopwords.get()
    keys_text = [x.lower() for x in keys_text if not x.isdigit() and x not in stop_words and len(x) > 3]
    keys_elements = [x.lower() for x in keys_elements if not x.isdigit() and x not in stop_words and len(x) > 3]
    res = compare_words(model_wrapper, " ".join(keys_text), " ".join(keys_elements))

    keys_text = set(re_keywords(model_wrapper, descriptive_element))
    keys_elements = set()
    for el in table.find_by_xpath(".//*[td or th or tr]", driver):
        keys_elements.update(set(re_keywords(model_wrapper, el.get_text(driver))))

    if res < LIMIT and keys_text and not (keys_elements & keys_text):
        bad_elem = [{
            "element": table,
            "problem": "Descriptive elements available on table do not describe the table well"
        }]
    return bad_elem


def wcag(driver: webdriver, table: Element, model_wrapper):
    """
    H73: Using the summary attribute of the table element to give an overview of data tables_false
    WSAG: https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/H73
    """
    bad_elems = []
    captions = []
    summary = table.get_attribute(driver, "summary")
    caption = table.find_by_xpath(".//caption[text()]", driver)
    if summary:
        if len(caption) > 0:
            captions.append(dict(caption=caption[0]))
            if summary == caption[0].get_text(driver):
                bad_elems.append({
                    "element": caption[0],
                    "problem": "The summary attribute should't duplicate caption information"
                })
            else:
                bad_elems.extend(describes_table(driver, table, caption[0].get_text(driver), model_wrapper))
        bad_elems.extend(describes_table(driver, table, summary, model_wrapper))
    else:
        return [], []
    return bad_elems, captions


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    bad_elements = []
    captions = []
    model_wrapper = dependencies["spacy_en_lg"]
    if dependencies["test_base_tables"]["status"] != "PASS":
        return dict(status="NOELEMENTS", message="Don't have tables on page", checked_elements=[])
    tables = [elem['table'] for elem in dependencies["test_base_tables"]['tables']]

    def check_table(table):
        elems, cap = wcag(webdriver_instance, table, model_wrapper)
        bad_elements.extend(elems)
        captions.extend(cap)

    Element.safe_foreach(tables, check_table)

    if bad_elements:
        return dict(status="FAIL", message="Incorrectly designed table", elements=bad_elements, captions=captions,
                    checked_elements=tables)
    elif bad_elements is None:
        return dict(status="NOELEMENTS", message="Table don't have attribute summary", checked_elements=tables)
    return dict(status="PASS", message="The tables complies with the requirements WSAG", elements=bad_elements,
                captions=captions, checked_elements=tables)
