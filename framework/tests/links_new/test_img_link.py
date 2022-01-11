from selenium import webdriver
from time import sleep

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.links_new.lib import img_description_is_present, is_visible, get_pseudo_element_attribute, \
    pseudo_element_description_is_present, alt_duplicates_text_description


framework_version = 5

# 1.1.1 и 2.4.4 и 4.1.2
webdriver_restart_required = False
WCAG = '1.1.1'
name = "Ensures that image links are implemented correctly and have meaningful names (1.1.1, 2.4.4, 4.1.2)"
elements_type = "link"
test_data = [
    {
        "page_info": {
            "url": "links_new/img/page_bug_test_img_link.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 2
        }
    },
    {
        "page_info": {
            "url": "links_new/img/page_bug_test_img_link_2.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "links_new/img/page_bug_test_img_link_3.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "links_new/img/page_good_test_img_link.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/img/page_good_test_img_link_2.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/img/page_good_test_img_link_3.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/img/page_good_test_img_link_4.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/img/page_good_test_img_link_5.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/img/page_good_test_img_link_6.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/img/page_good_test_img_link_7.html"
        },
        "expected_status": "PASS"
    },
]

"""
Для ссылок-картинок нужно, чтобы был реализован один из вариантов 
(1.1.1 и  2.4.4 и 4.1.2): 

- есть текстовое описание, включенное в ссылку + alt=”” 

- текстового описания нет + alt=”” + aria-label=”some text” (или aria-labelledby) 

- текстового описания нет + alt=”some text”  
"""


def detect_background_image(driver: webdriver.Firefox, element: Element):
    descendants = element.find_by_xpath('descendant-or-self::*', driver)
    return (element.find_by_xpath('descendant::*[self::img or self::i]', driver)
            or any(i.get_element(driver).value_of_css_property('background-image') != 'none'
                   or get_pseudo_element_attribute(driver, i, 'before') != 'none'
                   or get_pseudo_element_attribute(driver, i, 'after') != 'none' for i in descendants))


def check_duplicates(driver: webdriver.Firefox, result: dict, body: Element, element: Element):
    if alt_duplicates_text_description(element, driver, body):
        element = dict(element=element, problem="alt duplicates text description",
                       severity="FAIL" if is_visible(element, driver) else "WARN",
                       error_id="duplicate-alt")
        result["elements"].append(element)


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    body = element_locator.get_all_of_type(webdriver_instance, element_types=['body'])[0]
    links = element_locator.get_all_of_type(webdriver_instance, element_types=['a'])
    if not links:
        return {'status': "NOELEMENTS", 'message': 'There are no links for testing.', 'elements': [],
                'checked_elements': []}
    result = {'status': "PASS", 'message': 'All img links found have a text description.', 'elements': [],
              'checked_elements': [], 'links_with_descr': []}

    def check_link(link: Element):
        if len(link.find_by_xpath('descendant::*[self::img or self::i]', webdriver_instance)) != 1:
            return
        result['checked_elements'].append(link)
        description = img_description_is_present(link, webdriver_instance, body)
        if not description:
            element = dict(element=link, problem="The img/i link doesn't have a description.",
                           severity="FAIL" if is_visible(link, webdriver_instance) else "WARN", error_id="image-link")
            result["elements"].append(element)
        else:
            check_duplicates(webdriver_instance, result, body, link)
            result['links_with_descr'].append((link, description, 'image'))
    Element.safe_foreach(links, check_link)

    def check_link_with_pseudo_element(link: Element):
        if not detect_background_image(webdriver_instance, link) or link in result['checked_elements']:
            return
        result['checked_elements'].append(link)
        description = pseudo_element_description_is_present(link, webdriver_instance, body)
        if not description:
            element = dict(element=link, problem="The link with pseudo attribute doesn't have a description.",
                           severity="FAIL" if is_visible(link, webdriver_instance) else "WARN", error_id="pseudo-link")
            result["elements"].append(element)
        else:
            check_duplicates(webdriver_instance, result, body, link)
            result['links_with_descr'].append((link, description, 'image'))
    Element.safe_foreach(links, check_link_with_pseudo_element)
    if result['elements']:
        result['status'] = 'FAIL'
        result['message'] = 'Found img links without a description!'
    print(result)
    return result
