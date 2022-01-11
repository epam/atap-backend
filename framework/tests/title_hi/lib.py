import re
from collections import defaultdict

from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.is_visible import is_visible
from framework.libs.phrases_distance import distance

NUMBER_OF_ANCESTORS = 10


def clean_html(raw_html):
    """Clear html code from html elements"""
    return re.sub('[@#$&{}()">]', ' ', re.sub(re.compile('<[\w\W]*?>'), '', raw_html)).strip()


def get_distance(model_wrapper, stop_words, text_first, text_second):
    return model_wrapper.run(
        distance,
        words_1=[w for w in text_first.lower().split() if w not in stop_words],
        words_2=[w for w in text_second.lower().split() if w not in stop_words]
    )


def get_distance_between_words(model_wrapper, word_first, word_second):
    return model_wrapper.run(
        distance,
        words_1=word_first.lower(),
        words_2=word_second.lower()
    )


def text(elem: Element, force=False):
    source = elem.source if isinstance(elem, Element) else elem
    return re.sub('[^A-Za-z ]+', '', clean_html(source)) if force else clean_html(source)


def find_next_header(i, tag, sorted_headers):
    for header in sorted_headers[i:]:
        if header.tag_name <= tag:
            return header
    return None


def split_body_text(body_text: str, current_header_text: str, next_header_text: str):
    i = body_text.find(current_header_text)
    j = body_text.find(next_header_text) if next_header_text is not None else 0
    return body_text[i + len(current_header_text):] if j == 0 else body_text[i + len(current_header_text):j]


def get_headers(driver: webdriver.Firefox, element: Element):
    return [h for h in element.safe_operation_wrapper(lambda e: e.find_by_xpath(
        'descendant::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6]', driver), on_lost=lambda: [])
            if is_visible(h, driver)]


def get_ancestor_with_another_headers(driver: webdriver.Firefox, header: Element):
    ancestors = header.find_by_xpath('ancestor-or-self::*', driver)[:-NUMBER_OF_ANCESTORS:-1]
    return next(iter(ancestor for ancestor in ancestors if len(get_headers(driver, ancestor)) >= 2), ancestors[-1])


def get_levels(driver: webdriver.Firefox, element_locator: ElementLocator):
    elements = element_locator.get_all_of_type(driver, element_types=['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    levels = defaultdict(list)
    for element in elements:
        if not is_visible(element, driver):
            continue
        ancestor = get_ancestor_with_another_headers(driver, element)
        levels[ancestor].append(element)
    return levels


def get_headers_structure(driver: webdriver.Firefox, element_locator: ElementLocator):
    """Parse the html page, from there for each header extract the corresponding text"""

    structure = dict()
    ancestor: Element
    for ancestor, headers in get_levels(driver, element_locator).items():
        ancestor_text = ancestor.get_text(driver)
        headers = [h for h in get_headers(driver, ancestor) if h in headers]
        for i, header in enumerate(headers):
            next_header = find_next_header(i + 1, header.tag_name, headers)
            header_text = header.get_text(driver)
            source = split_body_text(ancestor_text, header_text, next_header if next_header is None else next_header.get_text(driver))
            ancestor_text = ancestor_text[ancestor_text.find(header_text) + len(header_text):]
            structure[header] = source.strip()
    return structure
