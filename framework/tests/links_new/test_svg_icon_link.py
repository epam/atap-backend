from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.links_new.lib import svg_description_is_present, is_visible


framework_version = 5
webdriver_restart_required = False
# 1.1.1 и 2.4.4 и 4.1.2
WCAG = '1.1.1'
name = "Ensures that svg icon links are implemented correctly (1.1.1, 2.4.4, 4.1.2)"
elements_type = "link"
test_data = [
    {
        "page_info": {
            "url": "links_new/svg/page_good_svg_link.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/svg/page_good_svg_link_2.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/svg/page_good_svg_link_text.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/svg/page_good_svg_link_role_img.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/svg/page_bug_svg_link.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "links_new/svg/page_bug_svg_link_2.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    },
    {
        "page_info": {
            "url": "links_new/svg/page_bug_svg_link_role_img.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    }
]

"""
SVG иконки-ссылки (1.1.1 и  2.4.4 и 4.1.2).  

1) Должен быть aria-label (или aria-labelledby или title) у ссылки (https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA7 
и https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA8) 

2) Текст внутри ссылки и просто svg  иконка  

3) Ссылка без ариа-лейбла, но svg role=img + aria-labelledby=”x”, внутри svg элемент с  id=”x” 
(пример https://weboverhauls.github.io/demos/svg/#links) 
"""


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    body = element_locator.get_all_of_type(webdriver_instance, element_types=['body'])[0]
    links = element_locator.get_all_of_type(webdriver_instance, element_types=['a'])
    if not links:
        result = {'status': "NOELEMENTS", 'message': 'There are no links for testing.', 'elements': [],
                  'checked_elements': []}
        print(result)
        return result
    result = {'status': "PASS", 'message': 'All svg link icons found have a text description.', 'elements': [],
              'checked_elements': links, 'links_with_descr': []}
    counter = 1

    def check_link(link: Element):
        nonlocal counter
        print(f'\rAnalyzing links {counter}/{len(links)}', end="", flush=True)
        counter += 1
        if all(x.tag_name != 'svg' for x in link.find_by_xpath('descendant::*', webdriver_instance)):
            return
        description = svg_description_is_present(webdriver_instance, body, link)
        if not description:
            result["elements"].append({"element": link, "problem": "The svg link icon doesn't have a description.",
                                       "severity": "FAIL" if is_visible(link, webdriver_instance) else "WARN"})
        else:
            result['links_with_descr'].append((link, description, 'svg'))
    Element.safe_foreach(links, check_link)
    if result['elements']:
        result['status'] = 'FAIL'
        result['message'] = 'Found svg icons links without a description!'
    print(result)
    return result
