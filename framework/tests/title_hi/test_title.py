import re
import tempfile
from time import sleep
from urllib.parse import urlparse
from string import punctuation, whitespace

from bs4 import BeautifulSoup
from selenium import webdriver

from framework.libs.keywords_getter import KeywordsGetter
from framework.element_locator import ElementLocator
from framework.element import Element
from framework.element_wrapper import ElementWrapper
from framework.activity import Activity
from framework.tests.title_hi.lib import text
from framework.libs.stop_words import cached_stopwords
from framework.libs.stemmer import cached_stemmer
from framework.tests.title_hi.lib import get_distance

name = "Ensures that <title> element describes the purpose of the page"
depends = ['word2vec_googlenews']
framework_version = 5
WCAG = '2.4.2'
elements_type = ""
webdriver_restart_required = True
test_data = [
    {
        "page_info": {
            "url": "title_header/page_good_title.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "title_header/page_good_title_2.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "title_header/page_bugs_header_title.html"
        },
        "expected_status": "FAIL"
    }
]
STOP_PHRASES = ['document', 'page', 'title', 'default', 'new', 'untitled']
DOMAINS = ['.com', '.ru', '.org', '.net', '.int', '.edu', '.gov', '.mil', '.uk', '.us', '.eu', '.html']
GREEN_WORDS = ['about']


def title_contains_stop_phrases(title_text: str) -> bool:
    return all([word.lower() in STOP_PHRASES or word.isdigit() for word in re.findall(r"[\w']+", title_text)])


def get_body_text_and_headers_from_iframe(element_locator: ElementLocator, driver: webdriver.Firefox):
    iframes = element_locator.get_all_of_type(driver, ['iframe'])
    body_text = ""
    headers = {'h1': [], 'h2': []}
    for iframe in iframes:
        driver.switch_to.frame(iframe.get_element(driver))
        body_text += driver.find_element_by_tag_name('body').text
        for tag_name in ['h1', 'h2']:
            for header in driver.find_elements_by_tag_name(tag_name):
                wrap = ElementWrapper(header, driver)
                if wrap.is_visible and wrap.text:
                    headers[tag_name].append(wrap.text)
        driver.switch_to.default_content()
    return (body_text, " ".join(headers['h1']), 'h1') if headers['h1'] else (body_text, " ".join(headers['h2']), 'h2')


def get_keywords(body_text, stemmer, stop_words):
    body_words = set(body_text.lower().split())
    if len(body_words) < 20:
        body_words = {stemmer.stem(word) for word in body_words if (word not in stop_words or word in GREEN_WORDS)
                      and len(word) > 3}
        return {word: 1 / len(body_words) for word in body_words}
    return {x[0]: x[1] for x in KeywordsGetter(body_text).get_keywords_using_gensim(need_scores=True)}


def compare_title_and_text(element_locator, driver, title, model_wrapper):
    body_text = element_locator.get_all_by_xpath(driver, "//body")[0].get_text(driver).lower()
    body_text_from_iframe, header_text_from_iframe, header_tag = get_body_text_and_headers_from_iframe(element_locator, driver)
    stem = cached_stemmer
    stop_words = cached_stopwords.get()
    keywords = get_keywords(body_text, stem, stop_words)
    title_text = text(title, force=True).lower()
    filtered_title_text = " ".join([stem.stem(word) for word in title_text.split()
                                    if (word not in stop_words or word in GREEN_WORDS) and len(word) > 3])
    window_height = driver.get_window_size()['height']
    h1 = [wrap for wrap in [ElementWrapper(h, driver) for h in element_locator.get_all_by_xpath(driver, '//h1')]
          if wrap.is_visible and list(wrap.location)[1] < window_height / 1.65]
    h2 = [wrap for wrap in [ElementWrapper(h, driver) for h in element_locator.get_all_by_xpath(driver, '//h2')]
          if wrap.is_visible and list(wrap.location)[1] < window_height / 2.5]
    if h1 or h2 or header_text_from_iframe:
        if h1 or h2:
            header_text = (" ".join([text(h.framework_element, force=True) for h in h1]) if h1
                           else " ".join([text(h.framework_element, force=True) for h in h2]))
            header_tag = 'h1' if h1 else 'h2'
        else:
            body_text += " " + body_text_from_iframe
            header_text = header_text_from_iframe
        header_text = header_text.lower()
        words = set([stem.stem(word) for word in header_text.split()
                     if (word not in stop_words or word in GREEN_WORDS) and len(word) > 3])
        number_of_words = len(words)
        keywords.update({word: 1 / number_of_words if word not in keywords else keywords[word] for word in words})
    else:
        counter = sum(1 * score if filtered_title_text.find(word) != -1 else 0 for (word, score) in keywords.items())
        return counter > 0.3 and get_distance(model_wrapper, stop_words, body_text, text(title)) < 4.35
    counter = sum(1 * score if filtered_title_text.find(word) != -1 else 0 for (word, score) in keywords.items())
    distance_between_h_and_title = (0 if (header_text in title_text or title_text in header_text)
                                    else get_distance(model_wrapper, stop_words, header_text, text(title).lower()))
    return ((counter > 0.23 if len(filtered_title_text.split()) < 3 else
             (counter > 0.34 if len(filtered_title_text.split()) < 6 else counter > 0.74))
            and distance_between_h_and_title < (3.85 if header_tag == 'h1' else 2.2))


def title_is_url(title: Element, url: str):
    title_text = text(title, force=False).lower()
    return urlparse(title_text).scheme or url in title.source or title_text.startswith('www.') or any(
        title_text.endswith(domain) or title_text.endswith(domain + '/') for domain in DOMAINS)


def title_is_empty(title: str):
    return all(i.isdigit() or i in punctuation or i in whitespace for i in title)


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator, dependencies):
    """Testing the page title: keyword method"""

    conclusion = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': []}
    activity.get(webdriver_instance)
    sleep(2)

    title = element_locator.get_all_by_xpath(webdriver_instance, "//head//title")
    if not title:
        conclusion['status'] = 'NOELEMENTS'
        conclusion['message'] = 'The title is absent.'
        return conclusion

    file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    webdriver_instance.save_screenshot(file.name)
    model_wrapper = dependencies['word2vec_googlenews']
    title = title[0]
    title_text = BeautifulSoup(title.source, 'lxml').title.get_text().lower().strip()
    if not title_text:
        return conclusion
    conclusion['checked_elements'].append(title)
    if title_is_empty(title_text) or title_contains_stop_phrases(title_text) or title_is_url(title, activity.url):
        conclusion["elements"].append({"element": title,
                                       "problem": "The title does not match the text on the page",
                                       "severity": "FAIL",
                                       "screenshot": file.name})
    elif not compare_title_and_text(element_locator, webdriver_instance, title, model_wrapper):
        conclusion["elements"].append({"element": title,
                                       "problem": "The title does not match the text on the page",
                                       "severity": "WARN",
                                       "screenshot": file.name})
    if conclusion["elements"]:
        conclusion["status"] = "FAIL"
    print(conclusion)
    return conclusion
