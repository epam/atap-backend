import string
import time
import re
import numpy as np
from gensim.summarization.summarizer import summarize

from framework.libs.keywords_getter import KeywordsGetter
from framework.tests.title_hi.lib import get_headers_structure
from framework.libs.distance_between_elements import distance
from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.stop_words import cached_stopwords
from framework.libs.stemmer import cached_stemmer
from framework.tests.title_hi.get_definition import get_definition, get_synonyms
from framework.tests.title_hi.get_Ngrams import get_ngrams
from framework.libs import spacy_model_interface


name = "Ensures that <h1>-<h6> elements well express the semantic content of the texts relating to them"
depends = ['spacy_en_lg']
webdriver_restart_required = False
framework_version = 5
WCAG = '2.4.6'
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "title_header/page_good_header.html"
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

THRESHOLD = 0.4
SIMILARITY_THRESHOLD = 0.35
NGRAMS_THRESHOLD = 2e-06

EPSILON = 15

GREEN_LIST = ['faq', 'note', 'reference', 'menu', 'navigation', 'introduction', 'conclusion', 'summary',
              'content', 'section', 'fact', 'tag', 'post', 'galleri', 'headlin', 'commit']


class TestHeader:
    def __init__(self, driver, element_locator, model_wrapper):
        self.dr = driver
        self.loc = element_locator
        self.model_wrapper = model_wrapper
        self.stemmer = cached_stemmer
        self.stop_words = cached_stopwords.get()

    @staticmethod
    def check_header_len(header):
        words = re.findall(r"[\w']+", header.strip())
        return len(header) > 75 or sum([len(i) > 2 for i in words]) > 10

    @staticmethod
    def header_is_not_valid(header):
        words = re.findall(r"[\w']+", header.strip())
        sum_digits_and_punctuation = sum([i.isdigit() or i in string.punctuation for i in words])
        return (all(i.isdigit() or i in string.punctuation for i in header)
                or sum_digits_and_punctuation > len(words) - sum_digits_and_punctuation
                or all(any(i.isdigit() for i in word) and any(i.isalpha() for i in word) for word in words))

    def get_common_ancestor(self, elem1: Element, elem2: Element):
        ancestors1 = elem1.safe_operation_wrapper(lambda e: e.find_by_xpath('ancestor::*', self.dr), on_lost=lambda: [])[::-1]
        ancestors2 = elem2.safe_operation_wrapper(lambda e: e.find_by_xpath('ancestor::*', self.dr), on_lost=lambda: [])[::-1]
        for ancestor in ancestors1:
            if ancestor in ancestors2:
                return ancestor
        return None

    def located_side_by_side_in_html_tree(self, elem1: Element, elem2: Element):
        ancestor: Element = self.get_common_ancestor(elem1, elem1)
        children = ancestor.find_by_xpath('child::*', self.dr)
        for child1, child2 in zip(children, children[1:]):
            if child1 == elem1 and child2 == elem2 or child1 == elem2 and child2 == elem1:
                return True
        return False

    def located_next_to(self, element_1: Element, element_2: Element):
        """
        Checks that elements are close to each other visually or in the house(have a common ancestor)
        """
        return distance(self.dr, element_1, element_2) < EPSILON and self.located_side_by_side_in_html_tree(element_1, element_2)

    def result(self):
        text_struct = get_headers_structure(self.dr, self.loc)
        result = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': []}
        if not text_struct.items():
            result['status'] = 'NOELEMENTS'
            return result

        previous_elem = None
        header_elem: Element
        for i, (header_elem, text) in enumerate(text_struct.items()):
            header = header_elem.get_text(self.dr).lower().strip()
            if not header:
                continue
            result['checked_elements'].append(header_elem)
            print(f'\rAnalyzing headers {i + 1}/{len(text_struct.items())}', end="", flush=True)
            if previous_elem is not None and self.located_next_to(previous_elem, header_elem):
                result["elements"].append({"element": header_elem,
                                           "problem": f"You need to combine this header with {previous_elem}",
                                           "severity": "FAIL", "error_id": "combine_headers"})
                result["elements"].append({"element": previous_elem,
                                           "problem": f"You need to combine this header with {header_elem}",
                                           "severity": "FAIL", "error_id": "combine_headers"})
            if self.header_is_not_valid(header):
                result["elements"].append({"element": header_elem,
                                           "problem": "The header is incorrect.",
                                           "severity": "FAIL"})
            elif not text:
                result["elements"].append({
                    "element": header_elem,
                    "problem": "The header(<h1>-<h6>) has no content.",
                    "error_id": "HeaderHasNoContent",
                    "severity": "FAIL"
                })
            elif (self.check_header_len(header) or not self.compare_header_with_keywords(header, text)
                  and not self.compare_header_with_summary(header, text)
                  and not self.compare_header_with_text_using_definition(header, text)
                  and not self.compare_header_with_text_using_synonyms(header, text)
                  and not self.compare_ngrams_using_definition(header, text)):
                result["elements"].append({
                    "element": header_elem,
                    "problem": "This header does not describe the content of the subsequent text well.",
                    "severity": "WARN"})
            previous_elem = header_elem
        if result["elements"]:
            result["status"] = "FAIL"
        print(result)
        return result

    def compare_header_with_text_using_definition(self, header, text):
        """Testing by dragging their definitions and synonyms to the title words"""
        if len(self.filter_text(header)) > 2:
            return False
        text = set(self.filter_text(text))
        header = self.filter_text(header, need_stem=False)
        keywords = set(header)
        for word in header:
            word = self.stemmer.stem(word)
            definition = get_definition(word)
            if not definition:
                continue
            getter = KeywordsGetter(definition)
            keywords = keywords.union(getter.get_keywords_using_spacy(self.model_wrapper)).union(getter.get_keywords_using_gensim())
        keywords = {word for word in keywords if len(word) > 3 and word not in self.stop_words}
        return keywords.intersection(text)

    def compare_ngrams_using_definition(self, header, text):
        ngrams_sum = get_ngrams(content=header, start_year=1999, end_year=2019, smoothing=3, case_insensitive=True).sum()
        if len(self.filter_text(header)) > 4 or ngrams_sum.size and ngrams_sum.iloc[1] < NGRAMS_THRESHOLD:
            return False
        definition = get_definition(header)
        if not definition:
            return False
        header = self.filter_text(header, need_stem=False)
        keywords = set(header)
        getter = KeywordsGetter(definition)
        keywords = keywords.union(getter.get_keywords_using_spacy(self.model_wrapper)).union(getter.get_keywords_using_gensim())
        keywords = {word for word in keywords if len(word) > 3 and word not in self.stop_words}
        return keywords.intersection(text)

    def compare_header_with_text_using_synonyms(self, header, text):
        if len(self.filter_text(header)) > 2:
            return False
        text = self.filter_text(text)
        header = self.filter_text(header)
        synonyms = set(header)
        for word in header:
            synonyms = synonyms.union(self.stemmer.stem(word) for word in get_synonyms(word) if word not in self.stop_words)
        return synonyms.intersection(text)

    def compare_header_with_summary(self, header: str, text: str):
        """Testing by comparing  header and annotation to text"""
        header_text = self.filter_text(header)
        try:
            abstract = summarize(text).lower()
        except ValueError:
            return True
        if not abstract:
            return True
        return header_text and sum(word in abstract for word in header_text) / len(header_text) > THRESHOLD

    @staticmethod
    def delete_punctuation(string_: str) -> str:
        return string_.translate(str.maketrans('', '', string.punctuation))

    def filter_text(self, text: str, need_stem=True):
        return [self.stemmer.stem(word) if need_stem else word for word in self.split(text.lower()) if word not
                in self.stop_words and len(word) > 2]

    def join_and_create(self, word_list: list):
        """
        Function to summarise the words listed in specified list for further vector creation.
        word_list  = <list> contains words or collocations as strings
        """
        common_doc = " ".join(word_list)
        return spacy_model_interface.create_doc(self.model_wrapper, common_doc).vector

    @staticmethod
    def get_norm(vector):
        return np.linalg.norm(vector)

    def check_similarity(self, header, keywords):
        header_vector = self.join_and_create(header)
        keywords_vector = self.join_and_create(keywords)
        norm = self.get_norm(header_vector)
        norm *= self.get_norm(keywords_vector)
        similarity = np.dot(header_vector, keywords_vector) / norm if not np.isclose(norm, 0.0) else -np.inf
        return similarity > SIMILARITY_THRESHOLD

    @staticmethod
    def split(text: str):
        return re.findall(r"[\w']+", text.strip())

    def compare_header_with_keywords(self, header, text) -> bool:
        """check the number of text keywords in the header"""
        header_words = set(self.filter_text(header))
        if (not text or not header_words
                or sum([word in GREEN_LIST for word in header_words]) / len(header_words) >= 0.5
                or len(header_words.intersection(self.filter_text(text))) / len(header_words) >= 0.5):
            return True
        getter = KeywordsGetter(text)
        keywords = set(getter.get_keywords_using_spacy(self.model_wrapper)).union(getter.get_keywords_using_gensim())
        keywords = self.filter_text(text) if not keywords else keywords
        if not keywords:
            return True
        return bool(header_words.intersection(keywords)) or self.check_similarity(header_words, keywords)


def test(webdriver_instance, activity, element_locator: ElementLocator, dependencies):
    """the main test runs, if necessary, other tests: test keyword test by using a summary, test definitions"""
    activity.get(webdriver_instance)
    time.sleep(2)
    return TestHeader(webdriver_instance, element_locator, dependencies['spacy_en_lg']).result()
