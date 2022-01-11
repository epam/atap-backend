from typing import List

import numpy as np
from selenium import webdriver
from selenium.webdriver.firefox.webelement import FirefoxWebElement

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.spacy_model_interface import create_doc
from framework.libs.distance_between_elements import distance
from framework.libs.is_visible import is_visible


name = '''Ensures that captcha image has audio alternative or satisfying description in alt-attribute'''
WCAG = '1.1.1'
framework_version = 4
depends = ["spacy_en_lg"]
webdriver_restart_required = False

elements_type = "captcha"
test_data = [
    {
        "page_info": {
            "url": "captcha/page_good_captcha.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "captcha/page_bugs_captcha.html"
        },
        "expected_status": "FAIL"
    }
]


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator, dependencies):
    """
    The course of the test:
    1) checked all the img elements and svg. If their code contains the word “captcha” and there is a field for
    entering captcha next to it, then a further check is started.
    2) it checks whether the img element has alt and the svg element has title/desc.
    3) it is a search for audio that belongs to the captcha. If there is audio, then the captcha is correct.
    4) If there is no audio, check_clarifications is started. It is necessary to check that the alt in the captcha
    describes its purpose. It works on the principle of searching for sensory characteristics in test_sensor_lang.
    Returns test result as a dict:
    result = {
                'status': <'ERROR', 'PASS', 'NOELEMENTS', 'FAIL>,
                'message': <string>,
                'elements': [{'source': Element, 'problem': <string>, 'error_id': <error_id>}, etc.],
                'checked_elements': [<element1>, <element2>, ...],
             }
    """
    activity.get(webdriver_instance)
    result = {'status': 'PASS',
              'message': '',
              'elements': [],
              'checked_elements': []}

    captcha, checked_elements = extract_captcha(webdriver_instance, element_locator, dependencies["spacy_en_lg"])
    if not checked_elements:
        result['status'] = 'NOELEMENTS'
    elif captcha:
        result['status'] = 'FAIL'
        result['elements'] = captcha
    result['checked_elements'] = checked_elements
    print(result)
    return result


def find_nearest_input_field(driver: webdriver.Firefox, media: Element, fields: List[FirefoxWebElement]):
    """
    Search for the nearest input field from the input list with type='text'
    """
    for field in fields:
        if is_visible(field, driver) and distance(driver, field, media) < 55:
            fields.remove(field)
            return field


def located_next_to(driver: webdriver.Firefox, element_1: Element, element_2: Element):
    """
    Checks that elements are close to each other visually or in the house(have a common ancestor)
    """
    return (is_visible(element_1, driver) and is_visible(element_2, driver) and distance(
        driver, element_1, element_2) < 50) or set(element_1.find_by_xpath('ancestor::*', driver)[-2:]).intersection(
        element_2.find_by_xpath('ancestor::*', driver)[-2:])


def detect_captcha(driver: webdriver.Firefox, image: Element, input_fields: List[FirefoxWebElement]):
    """
    Checking that the <svg> or <img> element is a captcha.
    Search for the keyword 'captcha' in the element code, if found, search next to the <input type='text'> element.
    """
    return ((image.source.lower().find('captcha') != -1 or
             image.get_parent(driver).source.lower().find('captcha') != -1) and
            find_nearest_input_field(driver, image, input_fields) is not None)


def check_alt_text_for_captcha(driver: webdriver.Firefox, image: Element, captcha: List[dict]):
    """
    Checking that alternative text is present for the captcha image (or the svg element contains <title> or <desc>)
    """
    if ((image.tag_name == 'svg' and not image.find_by_xpath('child::*[self::title or self::desc]', driver))
            or not image.get_attribute(driver, 'alt')):
        captcha.append({'element': image,
                        'problem': 'Captcha picture seems to have no alternative description.',
                        'error_id': 'CaptchaAlt',
                        'severity': 'FAIL'})


def extract_captcha(driver: webdriver.Firefox, element_locator: ElementLocator, model_wrapper):
    """
    Extracts captcha-pictures with relevant information.
    Checks whether captcha description satisfy success criterion.
    """
    images = element_locator.get_all_of_type(driver, ['img', 'svg'])
    captcha = []
    checked_elements = []
    input_fields = driver.find_elements_by_xpath("//input[@type='text']")
    audios = element_locator.get_all_of_type(driver, ['audio'])
    for image in images:
        if not detect_captcha(driver, image, input_fields):
            continue
        checked_elements.append(image)
        check_alt_text_for_captcha(driver, image, input_fields)
        for audio in audios:
            if not located_next_to(driver, image, audio):
                continue
            audios.remove(audio)
            if 'captcha' in audio.source.lower():
                # Audio alternative for captcha is found
                break
            elif check_clarifications(image, driver, model_wrapper):
                # Good description in alt is found
                break
        else:
            # check a/button with text 'audio'
            audio = driver.find_elements_by_xpath("//button[contains(text(), 'audio') or contains(text(), 'Audio')]") +\
                    driver.find_elements_by_xpath("//a[contains(text(), 'audio') or contains(text(), 'Audio')]")
            if any([distance(driver, i, image) < 25 for i in audio]):
                continue

            # Captcha seems not to have audio or text satisfactory alternative
            captcha.append({'element': image,
                            'problem': 'Captcha picture seems to have no satisfactory description.',
                            'error_id': 'Captcha',
                            'severity': 'FAIL'})
    # There is no captcha on the website
    return captcha, checked_elements


def check_clarifications(captcha, driver, model_wrapper):
    """
    Starts if no audio is found. Checking that the captcha's alt describes its purpose.
    It works on the principle of searching for sensory characteristics in test_sensor_lang.
    """
    alt = captcha.get_attribute(driver, 'alt')
    if alt and len(alt) >= 5:
        scale_vector = create_doc(
            model_wrapper, ' '.join(['captcha', 'verification', 'robot', 'submit', 'verify'])).vector
        alt_vector = create_doc(model_wrapper, alt).vector
        similarity = np.dot(alt_vector, scale_vector) / (np.linalg.norm(alt_vector) * np.linalg.norm(scale_vector))
        return similarity > 0.7
