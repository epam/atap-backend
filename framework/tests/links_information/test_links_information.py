from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs import descriptions


framework_version = 0
webdriver_restart_required = False
WCAG = "2.4.4"
name = "Ensures that <a> elements have text explaining their purpose"
elements_type = "link"
test_data = [
    {"page_info": {"url": "link_info/page_good_link_information.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "link_info/page_bugs_link_information.html"}, "expected_status": "FAIL"},
]


def get_children(driver, elem):
    return elem.find_by_xpath("child::*", driver)


def title_from_html_code(html_code):
    if html_code.find("<title>") == -1:
        return ""
    html_code = html_code[html_code.find("<title>") + 7 :]
    return html_code[: html_code.find("</title>")]


def test(webdriver_instance, activity, element_locator: ElementLocator):
    """The main function of testing. Finds all links, selects them clickable.

    For them, looking for text that explains the purpose of the link.

    Then, go to the url of the link and compare the content of the page with the purpose of the link

    """

    activity.get(webdriver_instance)
    conclusion = {"status": "PASS", "message": "", "elements": [], "checked_elements": []}

    links = element_locator.get_all_of_type(webdriver_instance, element_types=["a"])
    if not links:
        conclusion["status"] = "NOELEMENTS"
        return conclusion

    counter = 1
    conclusion["checked_elements"].extend(links)

    def check_link(link):
        nonlocal counter
        print(f"\rChecking link {counter}/{len(links)}", end="", flush=True)
        counter += 1
        definition, flag_ignore = descriptions.definition_link(
            webdriver_instance, link, element_locator.get_all_by_xpath(webdriver_instance, "/html/body")[0]
        )

        if flag_ignore:
            return

        if not len(definition):
            conclusion["elements"].append(
                {
                    "element": link,
                    "problem": "The link does not have text explaining its purpose.",
                    "error_id": "PurposeInContext",
                }
            )

    Element.safe_foreach(links, check_link)
    if conclusion["elements"]:
        conclusion["status"] = "FAIL"
    return conclusion
