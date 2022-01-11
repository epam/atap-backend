from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator


framework_version = 0
WCAG = "1.3.1"
elements_type = "table"
webdriver_restart_required = False
locator_required_elements = ["table"]
# test_data = [
#     {
#         "page_info": {
#             "url": "tables/page_good_true_tables.html"
#         },
#         "expected_status": "PASS",
#         "expected_additional_content_length": {
#           "tables": 1
#         }
#     }
# ]


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    tables = []
    for tb in element_locator.get_all_by_xpath(webdriver_instance, "//table"):
        tables.append(dict(table=tb))
    print(f"====>Found tables: {len(tables)}")
    if tables:
        return dict(status="PASS", tables=tables)
    return dict(status="NOELEMENTS", message="No table on page")
