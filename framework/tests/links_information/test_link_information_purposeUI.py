import requests

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.keywords_getter import KeywordsGetter
from framework.libs import clean
from framework.libs import descriptions

framework_version = 0
WCAG = "2.4.4"
depends = ["spacy_en_lg"]
webdriver_restart_required = True
name = "Ensures that <a> elements has description of which is handing semantic content resource far refers <a>"
elements_type = "link"
test_data = [
    {"page_info": {"url": "link_info/page_good_link_information.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "link_info/page_bugs_link_information.html"}, "expected_status": "FAIL"},
]


def title_from_html_code(html_code):
    if html_code.find("<title>") == -1:
        return ""
    html_code = html_code[html_code.find("<title>") + 7 :]
    return html_code[: html_code.find("</title>")]


def test(webdriver_instance, activity, element_locator: ElementLocator, dependencies):
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
    model_wrapper = dependencies["spacy_en_lg"]
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
        result = element_locator.click(link, webdriver_instance)
        if result["action"] == "NEWTAB" or result["action"] == "PAGECHANGE":
            try:
                response = requests.get(result["url"])
            except requests.exceptions.InvalidSchema:
                return
            html_code = response.text
            title = set(clean.clean_html(title_from_html_code(html_code), True, True, True).split(" "))
            text_link = clean.clean_html(html_code, False, False, False)

            activity.get(webdriver_instance)
            getter = KeywordsGetter(text_link)
            keywords = getter.get_keywords_using_spacy(model_wrapper)
            keywords.extend(getter.get_keywords_using_gensim())
            keywords = set(keywords)
            keywords.update(title)

            testing = False
            for key in keywords:
                if key in definition:
                    testing = True
                    break
            if not testing:
                conclusion["elements"].append(
                    {
                        "element": link,
                        "problem": "The text explaining purpose of the link is not informative.",
                        "error_id": "PurposeInContext",
                    }
                )

    Element.safe_foreach(links, check_link)
    if conclusion["elements"]:
        conclusion["status"] = "FAIL"
    return conclusion
