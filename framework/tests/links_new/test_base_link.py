from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.links_new.lib import text_is_present, get_pseudo_element_attribute


elements_type = "link"
webdriver_restart_required = False
test_data = []


def is_empty_link(driver: webdriver.Firefox, link: Element) -> bool:
    return not (text_is_present(link, driver)
                or link.find_by_xpath('child::*', driver)
                or link.get_attribute(driver, 'data-img') is not None
                or link.get_element(driver).value_of_css_property('background-image') != 'none'
                or get_pseudo_element_attribute(driver, link, 'before') != 'none'
                or get_pseudo_element_attribute(driver, link, 'after') != 'none')


def href_bug(driver: webdriver.Firefox, link: Element) -> bool:
    # if href is not present and link has role != 'link'
    attributes = link.get_attributes(driver)
    return ('href' not in attributes or not attributes['href']) and ('role' not in attributes or attributes['role'] == 'link')


def display_none(driver: webdriver.Firefox, element: Element) -> bool:
    ancestors = element.find_by_xpath('ancestor-or-self::*', driver)[::-1]
    return any(ancestor.safe_operation_wrapper(lambda e: e.get_element(driver).value_of_css_property('display'),
                                               on_lost=lambda: '') == 'none' for ancestor in ancestors)


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    links = element_locator.get_all_of_type(webdriver_instance, element_types=['a'])
    result = {'status': "NOELEMENTS", 'message': '', 'elements': [], 'checked_elements': links, 'test_empty_link': [],
              'test_link_without_href': []}
    counter = 1

    def check_link(link: Element):
        nonlocal counter
        print(f'\rAnalyzing links {counter}/{len(links)}', end="", flush=True)
        counter += 1
        if is_empty_link(webdriver_instance, link):
            result["test_empty_link"].append({"element": link, "problem": "The link is empty.",
                                              "severity": "WARN" if display_none(webdriver_instance, link) else "FAIL"})
        if href_bug(webdriver_instance, link):
            result["test_link_without_href"].append({
                "element": link, "problem": "Link without the href attribute.",
                "severity": "WARN" if display_none(webdriver_instance, link) else "FAIL"})
    Element.safe_foreach(links, check_link)
    print(result)
    return result
