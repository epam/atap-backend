import requests
import operator
import re
from typing import List

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.keywords_getter import KeywordsGetter
from framework.libs import clean
from framework.libs.stop_words import cached_stopwords
from framework.libs.is_visible import is_visible
from framework.libs.compare_texts import similarity

framework_version = 5
WCAG = '2.4.4'
depends = ["spacy_en_lg", "test_svg_icon_link", "test_img_link"]
webdriver_restart_required = False
name = "Ensures that <a> elements has description of which is handing semantic content resource far refers <a>"
elements_type = "link"
test_data = [
    {
        "page_info": {
            "url": "link_info/page_good_link_info.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "link_info/page_bugs_link_information.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "link_info/page_bugs_stop_phrase_link_information.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "link_info/page_good.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "link_info/page_bugs_link_info.html"
        },
        "expected_status": "FAIL"
    }
]
STOP_WORDS = ['read', 'more', 'click', 'here', 'learn']


class LinkDescriptionChecker:
    def __init__(self, driver: webdriver.Firefox, dependencies, element_locator):
        self.dr = driver
        self.model_wrapper = dependencies["spacy_en_lg"]
        self.result = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': []}
        self.dependencies = dependencies
        self.locator = element_locator

    @staticmethod
    def page_info_using_requests(url: str):
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException:
            return "", ""

        if response.status_code != 200:
            return "", ""

        html_code = response.text
        title, text = from_html_code(html_code)
        title = set(filter(lambda x: len(x) > 2 and x not in cached_stopwords.get(),
                           clean.clean_html(title, True, True, True).split()))
        return title, text

    def check_link_description_using_keywords(self, link: Element, description: str):
        url = link.get_attribute(self.dr, 'href')
        if url is None:
            return
        title, text = self.page_info_using_requests(url)

        if not title or not text:
            title, text = self.open_url_in_new_tab(url)
            title = set(filter(lambda x: len(x) > 2 and x not in cached_stopwords.get(),
                               clean.clean_html(title, True, True, True).split()))
        keywords = KeywordsGetter(clean.clean_html(text, False, False, False)).get_keywords_using_gensim(
            need_scores=True)
        keywords.extend([(word, 1 / len(title) if len(title) < 6 else 2 / len(title)) for word in title])
        score = sum(
            1 * score if (description.find(word) != -1 or
                          max([self.model_wrapper.run(similarity, word, descr) for descr in description.split()]) > 0.45)
            else 0 for (word, score) in keywords)
        return score >= 0.34

    def check_link(self, link: Element, description: str, kind=None):
        bad_elements = self.result['elements']

        if not description:
            bad_elements.append({
                'element': link,
                'problem': 'The link has no description.',
                'error_id': 'LinkDescriptionEmpty',
                'severity': 'FAIL'
            })
            return
        if description_contains_stop_phrases(description) and kind is not None:
            bad_elements.append({
                'element': link,
                'problem': 'The text description of the link contains a stop phrase (read more, click here, etc).',
                'error_id': 'LinkDescriptionContainsStopPhrase',
                'severity': 'FAIL'
            })
            return

        element = {
            'element': link,
            'problem': 'The text explaining purpose of the link is not informative.',
            'error_id': 'LinkDescription',
            'severity': 'WARN'
        }
        res = self.check_link_description_using_keywords(link, description)
        if not res and kind == 'text':
            parent = link.find_by_xpath('ancestor::*', self.dr)
            parent = [p for p in parent[-3:] if p.tag_name == 'p'][0] if \
                (parent and 'p' in [p.tag_name for p in parent[-3:]]) else False
            if parent and len(parent.find_by_xpath('child::*', self.dr)) < 3:
                if self.check_link_description_using_keywords(link, parent.get_text(self.dr)):
                    element['error_id'] = 'LinkDescriptionBP'
            bad_elements.append(element)
        elif not res:
            bad_elements.append(element)

    def get_result(self):
        links = []
        for test_name, test_result in self.dependencies.items():
            if test_name.startswith('test_') and test_result['status'] in ['PASS', 'FAIL']:
                links.extend(test_result['links_with_descr'])
        links.extend([(elem, elem.get_text(self.dr), 'text') for elem in
                      self.locator.get_all_by_xpath(self.dr, xpath="//body//a[normalize-space(text())]")])
        if not links:
            self.result['status'] = 'NOELEMENTS'
            return self.result

        for i, (link, description, kind) in enumerate(links):
            print(f'Checking link {i + 1}/{len(links)}: {link}, {link.source[:200]}')
            description = clean.clean_html(description, True, False, True)
            if is_visible(link, self.dr):
                self.check_link(link, description, kind)
                self.result['checked_elements'].append(link)

        if self.result["elements"]:
            self.result["status"] = "FAIL"
        return self.result

    def open_url_in_new_tab(self, url: str):
        current_window = self.dr.current_window_handle
        self.dr.execute_script(f"window.open('{url}')")
        self.dr.switch_to.window(self.dr.window_handles[-1])
        try:
            title = WebDriverWait(self.dr, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "title"))
            ).get_attribute('outerHTML')
            body = WebDriverWait(self.dr, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            ).text
            for t in self.dr.find_elements_by_tag_name('title'):
                if set(clean.clean_html(t.get_attribute('outerHTML'), True, True, True).split()):
                    title = t.get_attribute('outerHTML')
                    break
            self.dr.close()
            self.dr.switch_to.window(current_window)
            return title, body
        except TimeoutException:
            body = self.dr.find_element_by_tag_name('body').text
            self.dr.close()
            self.dr.switch_to.window(current_window)
            return "", body


def from_html_code(html_code: str) -> (str, str):
    soup = BeautifulSoup(html_code, 'html.parser')
    for title in soup.find_all('title'):
        if 'head' in [p.name for p in title.find_parents()] and title.get_text():
            return title.get_text(), soup.html.get_text()
    return "", soup.html.get_text()


def description_contains_stop_phrases(description: str) -> bool:
    return all([word.lower() in STOP_WORDS or word.isdigit() for word in re.findall(r"[\w']+", description)])


def test(webdriver_instance, activity, element_locator: ElementLocator, dependencies):
    """The main function of testing. Finds all links, selects them clickable.

    For them, looking for text that explains the purpose of the link.

    Then, go to the url of the link and compare the content of the page with the purpose of the link

    """

    activity.get(webdriver_instance)
    checker = LinkDescriptionChecker(webdriver_instance, dependencies, element_locator)
    return checker.get_result()
