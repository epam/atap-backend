from selenium import webdriver
import time


from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs import descriptions

name = "Ensures that <img> element description does not duplicate the visible text."
depends = ["test_dependency_for_image"]
webdriver_restart_required = False
framework_version = 0
WCAG = "1.1.1"
elements_type = "image"
test_data = [
    {"page_info": {"url": "images/page_bug_image_with_text_tA.html"}, "expected_status": "WARN"},
    {"page_info": {"url": "images/page_good_image_with_text.html"}, "expected_status": "PASS"},
]
NOT_VISIBLE_DESCRIPTION_ATTRIBUTES = ["alt", "aria-label", "title", "longdesc"]


def get_children(driver, elem):
    return elem.find_by_xpath("child::*", driver)


def duplication_of_visible_text(description: dict, visible_text) -> bool:
    for descr_name in NOT_VISIBLE_DESCRIPTION_ATTRIBUTES:
        if descr_name in description and visible_text.find(description[descr_name]) != -1:
            return True
    return False


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    body = element_locator.get_all_by_xpath(webdriver_instance, "/html/body")[0]

    def get_visible_description_for_image(image):
        parent = image.get_parent(webdriver_instance)
        while len(get_children(webdriver_instance, parent)) == 1:
            parent = parent.get_parent(webdriver_instance)
        return parent.get_text(webdriver_instance).lower()

    time1 = time.time()
    activity.get(webdriver_instance)
    conclusion = {
        "status": "PASS",
        "message": "No problems found.",
        "elements": [],
        "checked_elements": [],
    }
    images = dependencies["test_dependency_for_image"]["images"]

    if not images:
        conclusion["status"] = "NOELEMENTS"
        return conclusion
    counter = 1
    counter_warn = 0

    def check_image(obj):
        nonlocal counter
        nonlocal counter_warn
        print(f"\rAnalyzing elements {counter}/{len(images)}", end="", flush=True)
        counter += 1
        conclusion["checked_elements"].append(obj["element"])
        description = descriptions.get_description_image(webdriver_instance, obj["element"], body, True)
        visible_text = obj["element"].safe_operation_wrapper(get_visible_description_for_image, lambda _: None)
        if visible_text is not None and duplication_of_visible_text(description, visible_text):
            conclusion["elements"].append(
                {
                    "element": obj["element"],
                    "problem": "Warning: Alternative text is present, but it duplicates the"
                    " fully visible text. The best practice is to use alternative"
                    " text that complements the visible text.",
                }
            )
            counter_warn += 1

    Element.safe_foreach(images, check_image)
    if counter_warn:
        conclusion["status"] = "WARN"
        conclusion["message"] = "Problems were found: the alternative text of images duplicates the visible one."
    print(f"test_image_textAlternative timer = {time.time() - time1}")
    return conclusion
