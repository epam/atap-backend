from selenium import webdriver
from framework.element import Element
from framework.element_locator import ElementLocator

'''
Test for detection groups fo elements (containers) with functionality
such as <form>.
Finds groups of native input elements like <input>, <textarea> and other,
create WARN for group of 4 or more elements.
See https://www.w3.org/WAI/tutorials/forms/grouping/
Don't use custom edit-box and disguised submit button
'''

locator_required_elements = ['div', 'input', 'span', 'label']
depends = ['test_radio_buttons', 'test_checkbox']

name = "Test for checking forms"

framework_version = 0
webdriver_restart_required = False

test_data = [
    {
        "page_info": {
            "url": "page_good_form.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_bugs_form.html"
        },
        "expected_status": "WARN",
        "expected_problem_count": 5
    }
]


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    elements = list()
    problem_elements = list()
    result = 'Problems with forms not found'
    status = 'PASS'

    checkboxes_el = dependencies['test_checkbox']['elements']

    native = webdriver_instance.find_elements_by_xpath('//input')
    native = [{'element': Element(el, webdriver_instance)} for el in native]

    radiogroups = dependencies['test_radio_buttons']['radio']
    radiogroups = [{'element': el} for el in radiogroups]

    disguised_forms = list()
    elements = checkboxes_el + radiogroups + native

    count = 0
    for i in range(1, len(elements) - 1):
        #element_locator.activate_element(elements[i-1]['element'])
        #element_locator.activate_element(elements[i]['element'])
        if neighbours_parent(elements[i-1]['element'], elements[i]['element'], webdriver_instance):
            count += 1
        else:
            count = 0
        if count >= 4:
            web_parent = elements[i]['element'].get_element(webdriver_instance).find_element_by_xpath('..')
            disguised_forms.append(web_parent)

    for container in disguised_forms:
        if container.tag_name != 'fieldset' or \
           'role="group"' not in container.source:
            problem_elements.append({'element': container, 'problem': "Form's grouping needs to be carried in the code using <fieldset> and etc. See WCAG 1.3.1 and 3.3.2"})

    if len(problem_elements) > 0:
        result = 'Some problems with forms found'
        status = 'WARN'

    return {
        "status": status,
        "message": result,
        "elements": problem_elements
    }


def element_visually_close(element1, element2):
    # selenium webdriver elements
    top_elem = element1
    bot_elem = element2
    if element1.location['y'] > element2.location['y']:
        top_elem = element2
        bot_elem = element1
    elif element1.location['y'] == element2.location['y']:
        if element1.location['x'] > element2.location['x']:
            top_elem = element2
            bot_elem = element1
            if top_elem.location['x'] + top_elem.size['width']*1.5 < bot_elem.location['x']:
                return False
    else:
        if top_elem.location['y'] + top_elem.size['height']*2 <= bot_elem.location['y']:
            return False
    return True


def neighbours_parent(element1, element2, webdriver_instance):
    # Element object
    selenium_element1 = element1.get_element(webdriver_instance)
    selenium_element2 = element2.get_element(webdriver_instance)
    parent1 = selenium_element2.find_element_by_xpath('..')
    parent2 = selenium_element2.find_element_by_xpath('..')
    if parent1.tag_name != 'body':
        if parent1 == parent2 and \
           element_visually_close(selenium_element1, selenium_element2):
            return True
        ancestor1 = parent1.find_element_by_xpath('..')
        ancestor2 = parent2.find_element_by_xpath('..')
        if ancestor1.tag_name != 'body' and ancestor1 == ancestor2 and \
           element_visually_close(selenium_element1, selenium_element2):
                return True
    return False
