from selenium import webdriver
import re

from framework.element import Element, ElementLostException


def get_pseudo_element_attribute(driver: webdriver.Firefox, element: Element, pseudo: str, attr: str = 'content') -> str:
    return driver.execute_script(f"return window.getComputedStyle(arguments[0], "
                                 f"':{pseudo}').getPropertyValue('{attr}');", element.get_element(driver))


def alt_duplicates_text_description(link: Element, driver: webdriver.Firefox, body: Element):
    image_children = link.find_by_xpath('descendant::img', driver)
    if not image_children:
        return False
    attributes = image_children[0].get_attributes(driver)
    alt = alt_present(attributes)
    if not alt:
        return False
    alt = alt.lower().strip()
    alt_words = alt.split()
    link_attributes = link.get_attributes(driver)
    text_description = text_is_present(link, driver) or aria_present(link_attributes, driver, body) or aria_present(attributes, driver, body)
    text_description = text_description.lower().strip()
    description_words = text_description.split()
    sum_1 = sum(word in text_description for word in alt_words) / len(alt_words) if alt_words else 0
    sum_2 = sum(word in alt for word in description_words) / len(description_words) if description_words else 0
    return (sum_1 >= 0.66 and sum_2 >= 0.66 or sum_1 == 1 or sum_2 == 1) and abs(len(alt_words) - len(description_words)) < 4


def clean_html(raw_html):
    """Clear html code from html elements"""
    return re.sub('[@#$&{}()">]', ' ', re.sub(re.compile('<[\w\W]*?>'), '', raw_html)).strip()


def text_is_present(link: Element, driver: webdriver.Firefox):
    if is_visible(link, driver):
        text = link.safe_operation_wrapper(lambda l: l.get_text(driver), on_lost=lambda: '').strip().split()
        span_descendants = link.safe_operation_wrapper(lambda x: x.find_by_xpath('descendant::span', driver), lambda: [])
        for span in span_descendants:
            if span.get_element(driver).value_of_css_property('display') != 'none':
                span_text = clean_html(span.source).strip().split()
                text.extend([s for s in span_text if s not in text])
        return ' '.join(text)
    else:
        return clean_html(link.source)


def check_display_none(element):
    return any(ancestor.value_of_css_property('display') == 'none' for ancestor in
               element.find_elements_by_xpath('ancestor-or-self::*'))


def is_visible(elem: Element, driver: webdriver.Firefox):
    def check_visible(e: Element):
        try:
            element = e.get_element(driver)
        except ElementLostException:
            return False
        return (element and element.size['width'] * element.size['height'] > 0 and element.is_displayed() and
                element.is_enabled())
    return elem.safe_operation_wrapper(check_visible, on_lost=lambda: False)


def aria_labelledby_is_present(attributes: dict, driver: webdriver.Firefox, parent: Element) -> str:
    if 'aria-labelledby' not in attributes:
        return ''
    idx = attributes['id'] if 'id' in attributes else ''
    aria_labelledby = list(filter(lambda x: x != idx, attributes['aria-labelledby'].split()))
    if not aria_labelledby:
        return ''
    text = ''
    for aria in aria_labelledby:
        elem = parent.find_by_xpath(f"descendant::*[@id='{aria}']", driver)
        if not elem or not text_is_present(elem[0], driver):
            return ''
        text += elem[0].get_text(driver) + ' '
    return text.strip()


def alt_present(attributes: dict) -> str:
    return attributes['alt'] if 'alt' in attributes else ''


def aria_label_present(attributes: dict) -> bool:
    return attributes['aria-label'] if 'aria-label' in attributes else ''


def aria_present(attributes: dict, driver: webdriver.Firefox, body: Element) -> bool:
    return aria_label_present(attributes) or aria_labelledby_is_present(attributes, driver, body) or title_is_present(attributes)


def img_description_is_present(link: Element, driver: webdriver.Firefox, body: Element) -> bool:
    link_attributes = link.get_attributes(driver)
    image_children = link.find_by_xpath('descendant::*[self::img or self::i]', driver)
    attributes = image_children[0].get_attributes(driver) if image_children else dict()
    text_present = text_is_present(link, driver)
    return ('alt' in attributes or image_children[0].tag_name != 'img') and (
            text_present or alt_present(attributes) or aria_present(link_attributes, driver, body)
            or aria_present(attributes, driver, body))


def pseudo_element_description_is_present(link: Element, driver: webdriver.Firefox, body: Element) -> bool:
    link_attributes = link.get_attributes(driver)
    children = link.find_by_xpath('descendant::*', driver)
    text_present = text_is_present(link, driver)
    return (text_present or aria_present(link_attributes, driver, body) or
            any(aria_present(i.get_attributes(driver), driver, body) for i in children))


def title_is_present(attributes: dict):
    return attributes['title'] if 'title' in attributes else ''


def aria_label_or_title_present(link: Element, driver: webdriver.Firefox) -> bool:
    attributes = link.get_attributes(driver)
    return title_is_present(attributes) or (attributes['aria-label'] if 'aria-label' in attributes else '')


def svg_with_role_img(link: Element, driver: webdriver.Firefox):
    svg = list(filter(lambda x: x.tag_name == 'svg', link.find_by_xpath('descendant::*', driver)))
    for e in svg:
        attributes = e.get_attributes(driver)
        if 'role' in attributes and attributes['role'] == 'img':
            return aria_labelledby_is_present(attributes, driver, e)
    return ''


def svg_description_is_present(webdriver_instance, body, link):
    return (aria_label_or_title_present(link, webdriver_instance)
            or aria_labelledby_is_present(link.get_attributes(webdriver_instance), webdriver_instance, body)
            or text_is_present(link, webdriver_instance) or svg_with_role_img(link, webdriver_instance))


def check_children(driver, link):
    return (link.safe_operation_wrapper(lambda e: e.find_by_xpath(
        'descendant::*[self::img or self::i]', driver), on_lost=lambda: False) or
        list(filter(lambda x: x.tag_name == 'svg', link.find_by_xpath('descendant::*', driver))))


def check_any_description_of_link_is_missing(driver, body, link):
    return (not text_is_present(link, driver) or len(text_is_present(link, driver).split()) < 2 or
            (check_children(driver, link) and (not img_description_is_present(link, driver, body) or
                                               not svg_description_is_present(driver, body, link))))
