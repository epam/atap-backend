from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.links_new.lib import aria_present, text_is_present
from framework.libs.phrases_distance import distance
from framework.libs.stop_words import cached_stopwords

framework_version = 5
webdriver_restart_required = False
depends = ["word2vec_googlenews"]
WCAG = "2.4.4"  # BP
name = "Ensures that links have title attribute that matches description."
elements_type = "link"
test_data = [
    {"page_info": {"url": "links_new/title/page_good.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "links_new/title/page_bug.html"}, "expected_status": "PASS"},
]


def title_analyze(driver, link, attributes, model_wrapper, stop_words):
    text = text_is_present(link, driver)
    image_attributes = (
        link.find_by_xpath("descendant::img", driver)[0].get_attributes(driver)
        if link.find_by_xpath("descendant::img", driver)
        else link.find_by_xpath("descendant::i", driver)[0].get_attributes(driver)
        if link.find_by_xpath("descendant::i", driver)
        else dict()
    )
    descr = text if text else image_attributes["alt"] if "alt" in image_attributes else ""
    descr_words = [w for w in descr.lower().split() if w not in stop_words]
    title_words = [w for w in attributes["title"].lower().split() if w not in stop_words]
    _distance = model_wrapper.run(distance, words_1=descr_words, words_2=title_words)
    return _distance >= 3


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    body = element_locator.get_all_of_type(webdriver_instance, element_types=["body"])[0]
    links = links = element_locator.get_all_by_xpath(webdriver_instance, "//a[@title]")

    if not links:
        return {
            "status": "NOELEMENTS",
            "message": "There are no links for testing.",
            "elements": [],
            "checked_elements": [],
        }

    result = {
        "status": "PASS",
        "message": "All links with title attribute are executed correctly.",
        "elements": [],
        "checked_elements": links,
    }
    counter = 1
    stop_words = cached_stopwords.get()

    def check_link(link):
        nonlocal counter
        print(f"\rAnalyzing links {counter}/{len(links)}", end="", flush=True)
        counter += 1
        attributes = link.get_attributes(webdriver_instance)
        if not aria_present(attributes, webdriver_instance, body) and title_analyze(
            webdriver_instance, link, attributes, dependencies["word2vec_googlenews"], stop_words
        ):
            result["elements"].append(
                {
                    "element": link,
                    "problem": "Title attribute does not match alt text or link text.",
                    "severity": "FAIL",
                }
            )

    Element.safe_foreach(links, check_link)
    if result["elements"]:
        result["status"] = "FAIL"
        result["message"] = "Found links with an invalid title attribute."
    return result
