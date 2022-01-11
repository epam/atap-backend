from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.element import ElementLostException
from framework.libs import descriptions

WCAG = "1.1.1"
# !!! disabled !!!
framework_version = 0
name = "Ensures that image links have a programmatically accessible description"
webdriver_restart_required = False
elements_type = "image"
test_data = [
    {"page_info": {"url": "link_image/page_good_link_image.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "link_image/page_bugs_link_image.html"}, "expected_status": "FAIL"},
]


STOP_WORDS = ["link", "image", "spacer", "picture", "alt", "alternative text", "scene", "photo"]
FLAG_FILENAMES = [".jpg", ".png", ".gif"]


def get_children_images(driver, elem):
    try:
        return elem.find_by_xpath("child::img", driver)
    except (StaleElementReferenceException, ElementLostException):
        return []


def get_children_links(driver, elem):
    try:
        return elem.find_by_xpath("child::a", driver)
    except (StaleElementReferenceException, ElementLostException):
        return []


def get_link_description(driver, link):
    link_aria_label = link.get_attribute(driver, "aria-label")
    link_aria_labelledby = link.get_attribute(driver, "aria-labelledby")
    title = link.get_attribute(driver, "title")
    text = link.get_text(driver)
    parent_text = ""
    if not text:
        parent_text = (
            link.get_parent(driver).get_text(driver)
            if len(get_children_links(driver, link.get_parent(driver))) == 1
            else ""
        )
    attributes = [link_aria_labelledby, link_aria_label, title, text, parent_text]
    attributes = [attr.lower() for attr in attributes if attr is not None and attr != ""]
    return attributes


def check_accessible_name_for_image_which_content_link(driver, image, image_description, link_description):
    """WCAG: https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/F89"""

    role_image = image.get_attribute(driver, "role")
    if (role_image == "presentation" or not image_description) and not link_description:
        return False
    return True


def check_filenames_in_alt(alt_text):
    for n in FLAG_FILENAMES:
        if alt_text.find(n) != -1:
            return True
    return False


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    conclusion = {
        "status": "PASS",
        "message": "The test checks links that are created using images.",
        "elements": [],
        "elements_with_error_Name": [],
        "elements_with_description": [],
        "checked_elements": [],
    }

    elements = element_locator.get_all_of_type(webdriver_instance, element_types=["a", "img"])
    links_with_image = [
        elem for elem in elements if get_children_images(webdriver_instance, elem) and elem.tag_name == "a"
    ]
    D_link = [
        elem
        for elem in elements
        if len(get_children_links(webdriver_instance, elem)) == 1 and elem.tag_name == "img"
    ]
    elements = links_with_image.extend(D_link) if D_link else links_with_image
    counter = 1

    if not elements:
        conclusion["status"] = "NOELEMENTS"
        return conclusion

    def check_image_link(elem):
        nonlocal counter
        print(f"\rAnalyzing elements {counter}/{len(elements)}", end="", flush=True)
        counter += 1
        link = elem if elem.tag_name == "a" else get_children_links(webdriver_instance, elem)[0]
        image = elem if elem.tag_name == "img" else get_children_images(webdriver_instance, elem)[0]
        conclusion["checked_elements"].append(link)
        image_description = descriptions.get_description_image(
            webdriver_instance, image, element_locator.get_all_by_xpath(webdriver_instance, "/html/body")[0], True
        )
        link_description = get_link_description(webdriver_instance, link)
        conclusion["elements_with_description"].append(
            {"element": link, "link_descr": link_description, "image_descr": image_description}
        )
        if not check_accessible_name_for_image_which_content_link(
            webdriver_instance, image, image_description, link_description
        ):

            conclusion["elements"].append(
                {
                    "element": link,
                    "problem": "Error: Failure of Success Criterion 1.1.1 due to omitting the "
                    "alt attribute or text alternative on img element. "
                    "https://www.w3.org/TR/WCAG20-TECHS/F65",
                    "error_id": "NonTextName",
                }
            )
            conclusion["elements_with_error_Name"].append(link)
            return

        if "alt" in image_description and (
            image_description["alt"] in STOP_WORDS
            or image_description["alt"].isdigit()
            or check_filenames_in_alt(image_description["alt"])
        ):
            conclusion["elements"].append(
                {
                    "element": link,
                    "problem": "Error: Failure of Success Criterion 1.1.1 and 1.2.1 due to "
                    "using text alternatives that are not alternatives (e.g., "
                    "filenames or placeholder text). "
                    "https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/F30.",
                    "error_id": "NonTextName",
                }
            )

    Element.safe_foreach(elements, check_image_link)

    if conclusion["elements"]:
        conclusion["status"] = "FAIL"
    return conclusion
