import numpy as np
from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.libs.keywords_getter import KeywordsGetter
from framework.element import Element
from framework.libs import spacy_model_interface
from framework.libs.is_visible import is_visible

name = 'Ensures that text content does not contain any sensory characteristics for operating the content.'
framework_version = 4
WCAG = '1.3.3'
depends = ["spacy_en_lg"]
webdriver_restart_required = False

elements_type = "text"
test_data = [
    {
        "page_info": {
            "url": "sensor_lang/page_bad_sensor_lang.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 6
        }
    },
    {
        "page_info": {
            "url": "sensor_lang/page_bad_sensor_lang_2.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 3
        }
    },
    {
        "page_info": {
            "url": "sensor_lang/page_good_sensor_lang.html"
        },
        "expected_status": "PASS"
    }
]
#  'color',
COLOR_LIST = ['colour', 'colored', 'red', 'black', 'white', 'yellow', 'green', 'purple', 'pink', 'blue', 'brown',
              'orange', 'light', 'dark', 'multicolored', 'violet', 'gray']
SHAPE_LIST = ['square', 'shaped', 'rectangular', 'circular', 'semicircular', 'oval', 'triangular', 'pentagonal',
              'hexagonal', 'heart-shaped', 'star-shaped', 'spiral', 'flat', ]
SIZE_LIST = ['little', 'large', 'small', 'big', 'short', 'long', ]
AREA_LIST = ['left', 'right', 'top', 'bottom', 'near', 'below', 'above', 'between', 'against', 'upper right corner',
             'lower']
ORIENTATION_LIST = ['horizontal', 'vertical', 'full screen mode', 'landscape', 'portrait', 'between', 'against']
SOUND_LIST = ['sound', 'signal', 'melody', 'alarm', 'indicator', 'sign']
ELEMENT_LIST = ['button', 'link', 'bar', 'menu', 'panel', 'icon', 'line', 'text', 'mark', 'tick', 'cross', 'image',
                'section', 'concept']
ACTION_LIST = ['read', 'press', 'see', 'look', 'click', 'select', 'choose', 'represent', 'found', 'take', "pertain",
               'avoid', ]
GREEN_LIST = ['alternate text', 'alternative text']
FEATURES = {'color': COLOR_LIST, 'shape': SHAPE_LIST, 'size': SIZE_LIST, 'area': AREA_LIST,
            'orientation': ORIENTATION_LIST, 'sound': SOUND_LIST, 'element': ELEMENT_LIST, 'action': ACTION_LIST}


ALL_LIST = AREA_LIST + ORIENTATION_LIST + ELEMENT_LIST + ACTION_LIST

SKIPPED_TAGS = ['script']


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator, dependencies):
    """
    Tests a web page for WCAG 1.3.3 criterion.
    Uses find_sensor_links for each body element's text.
    Only gives WARN, PASS and NOTRUN status flags.
    webdriver_instance = [selenium driver]
    url = [string] web page address
    Returns test result as a dict:
    result = {
                'status': <'WARN', 'PASS' or 'NOTRUN'>,
                'message': <string>,
                'elements': [{'source': <html code>, 'problem': <string>}, etc.]
             }
    """
    activity.get(webdriver_instance)
    return SensorLang(webdriver_instance, element_locator, dependencies["spacy_en_lg"]).result()


class SensorLang:
    def __init__(self, driver: webdriver.Firefox, element_locator: ElementLocator, model_wrapper):
        self.dr = driver
        self.locator = element_locator
        self.model_wrapper = model_wrapper
        self.checker = SensorLangDetection(self.model_wrapper)

    def result(self):
        return self.main()

    def main(self):
        elements = self.locator.get_all_by_xpath(self.dr, "//body//*[normalize-space(text())]")
        result = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': elements}

        def check(paragraph: Element):
            if (paragraph.get_attribute(self.dr, "hidden") is not None or not is_visible(paragraph, self.dr)
                    or paragraph.get_attribute(self.dr, "aria-hidden") == "true" or paragraph.tag_name in SKIPPED_TAGS):
                return
            if self.find_sensor_links(text=paragraph.get_text(self.dr).lower().strip()):
                report = 'References to sensor characteristics are found.'
                # for i in range(len(bad_sentences)):
                #     report += '\t' + '{}) '.format(i + 1) + bad_sentences[i][0] + '\n'
                #     report += '\t' + 'Found sensor characteristics: ' + str(bad_sentences[i][1])
                result['elements'].append({'element': paragraph, 'problem': report, 'severity': "WARN"})
        Element.safe_foreach(elements, check)
        if result['elements']:
            result['status'] = 'FAIL'
        return result

    @staticmethod
    def most_similar(word):
        """
        Function for finding top 10 similar word-vectors to the current word-vector:
        word = <spacy.tokens.token.Token>
        Returns a list with top 10 closest words (human readable text)
        """
        by_similarity = sorted(word.vocab, key=lambda w: word.similarity(w), reverse=True)
        return by_similarity[:15]

    def check(self, marker, token):
        """
        Compares the similarity of given token and marker to threshold to check if the token belongs to the marker group.
        marker = [string] key for vectors and thresholds dictionaries
        token = [spacy.tokens.token.Token] token to check
        Returns True and False
        """
        if marker in self.checker.pos and token.pos_ not in self.checker.pos[marker]:
            return False
        norm = self.checker.norms[marker] * np.linalg.norm(token.vector)
        similarity = np.dot(self.checker.vectors[marker], token.vector) / norm if not np.isclose(norm, 0.0) else -np.inf
        return similarity > self.checker.thresholds[marker]

    def find_sensor_links(self, text):
        """"
        Finds sentences, which contain sensory characteristics in describing actions, and returns them as a list of
        sentences.
        text = <string> text itself
        Returns a list of 'bad' sentences.
        """
        text = spacy_model_interface.create_doc(self.model_wrapper, text)
        return any(self.sent_analysis(sent) for sent in text.sents)

    @staticmethod
    def features_intersection(sent):
        features = set()
        words = set(token.lemma_ for token in sent)
        for marker in FEATURES.keys():
            if marker not in features and words.intersection(FEATURES[marker]):
                features.add(marker)
        return len(features) > 2 and 'element' in features and 'green' not in features and 'action' in features

    def sent_analysis(self, sent):
        tokens = [token for token in sent if token.pos_ in ['NOUN', 'PROPN', 'VERB', 'ADP', 'ADJ']
                  and (not token.is_stop or token.lemma_ in ALL_LIST)]
        if len(tokens) < 3:
            return False
        features = {marker for marker in FEATURES.keys() if set(token.lemma_ for token in tokens).intersection(FEATURES[marker])}
        for token in tokens:
            for marker in set(FEATURES.keys()) - features:
                if marker not in features and self.check(marker, token):
                    features.add(marker)
                    break
        return len(features) > 2 and 'element' in features and all(green not in sent.text for green in GREEN_LIST) and 'action' in features


class SensorLangDetection:
    def __init__(self, model_wrapper):
        self.model_wrapper = model_wrapper
        self.vectors = dict()
        self.norms = dict()
        for marker, feature in FEATURES.items():
            self.join_and_create(marker, feature)

        self.thresholds = {'color': np.float_(0.8), 'shape': np.float_(0.67), 'size': np.float_(0.78),
                           'area': np.float_(0.63), 'orientation': np.float_(0.7), 'sound': np.float_(0.7),
                           'element': np.float_(0.55), 'action': np.float_(0.45)}
        self.pos = {'element': ['NOUN', 'PROPN'], 'action': ['VERB', 'NOUN']}

    def join_and_create(self, marker: str, word_list: list):
        """
        Function to summarise the words listed in specified list for further vector creation.
        word_list  = <list> contains words or collocations as strings
        """
        common_doc = " ".join(word_list)
        self.vectors[marker] = spacy_model_interface.create_doc(self.model_wrapper, common_doc).vector
        self.norms[marker] = np.linalg.norm(self.vectors[marker])
