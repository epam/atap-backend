from collections import defaultdict
from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.radio_disabled import test_radio_disabled_textAlternative

depends = ["test_radio_buttons"]
webdriver_restart_required = True
framework_version = 5
WCAG = '4.1.2'
elements_type = "radio"
test_data = [
    {
        "page_info": {
            "url": "radio_disabled/page_bugs_radio_disabled.html"
        },
        "expected_status": "WARN"
    },
    {
        "page_info": {
            "url": "radio_disabled/page_good_radio_disabled.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "radio_disabled/page_bugs_radio_disabled_2.html"
        },
        "expected_status": "FAIL"
    }
]

name = "Ensures that radio buttons disabled after pressing the confirm button and have correct text description"


def find_not_disabled_radiogroups(driver, radiogroups):
    """  "disabled" attribute -  <input disabled>"""

    not_disabled_radiogroups = list()
    for radiogroup in radiogroups:
        for radio in radiogroup['radio_buttons']:
            children = test_radio_disabled_textAlternative.get_children(driver, radio)
            if not children:
                attributes = test_radio_disabled_textAlternative.get_all_attributes(driver, radio)
                if 'disabled' not in attributes.keys() and \
                        ('aria-disabled' not in attributes.keys() or ('aria-disabled' in attributes.keys() and
                                                                      attributes['aria-disabled'] != "true")):
                    not_disabled_radiogroups.append(radiogroup['element'])
                    break
            else:
                for child in children:
                    attributes = test_radio_disabled_textAlternative.get_all_attributes(driver, child)
                    if 'disabled' in attributes.keys() or ('aria-disabled' in attributes.keys() and
                                                           attributes['aria-disabled'] == "true"):
                        break
                else:
                    not_disabled_radiogroups.append(radiogroup['element'])
                    break
    return not_disabled_radiogroups


def find_not_clickable_radiogroups(driver, radiogroups):
    not_clickable_radiogroups = list()
    for radiogroup in radiogroups:
        not_clickable_radio = list()
        for radio in radiogroup['radio_buttons']:
            if radio.click(driver)['action'] == "NONINTERACTABLE":
                not_clickable_radio.append(radio)
        if len(not_clickable_radio) == len(radiogroup['radio_buttons']):
            not_clickable_radiogroups.append(radiogroup)
    return not_clickable_radiogroups


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    conclusion = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': []}
    radiogroups = dependencies["test_radio_buttons"]["radiogroups"]

    test_radio_disabled_textAlternative.get_standard_radiogroups(webdriver_instance, element_locator, radiogroups)
    if not radiogroups:
        conclusion['status'] = 'NOELEMENTS'
        return conclusion
    buttons, button_radiogroups_dict = test_radio_disabled_textAlternative.get_button_and_radiogroups_dict(
        webdriver_instance, list(), defaultdict(list), radiogroups)
    counter = 1
    counter_warn = 0
    counter_error = 0

    def check(key):
        nonlocal counter, counter_error, counter_warn
        print(f'\rAnalyzing radiogroups {counter}/{len(button_radiogroups_dict)}', end="", flush=True)
        counter += 1
        if not test_radio_disabled_textAlternative.activate_radio(webdriver_instance, button_radiogroups_dict[key]):
            # radio-s are not clickable
            return
        event, flag = test_radio_disabled_textAlternative.activate_button(webdriver_instance, buttons[key])
        if flag and test_radio_disabled_textAlternative.event_handing(webdriver_instance, event,
                                                                      button_radiogroups_dict[key], buttons[key]):
            not_disabled_radiogroups = find_not_disabled_radiogroups(webdriver_instance, button_radiogroups_dict[key])
            not_clickable_radiogroups = find_not_clickable_radiogroups(webdriver_instance, button_radiogroups_dict[key])
            for radiogroup in button_radiogroups_dict[key]:
                conclusion['checked_elements'].append(radiogroup['element'])
                if (radiogroup['element'] not in not_clickable_radiogroups and
                    radiogroup['element'] in not_disabled_radiogroups) or \
                        radiogroup['element'] in not_disabled_radiogroups:
                    conclusion['elements'].append({'element': radiogroup['element'],
                                                   'problem': 'WARN: Perhaps when passing radio buttons reader will not'
                                                              ' sound "dimmed"',
                                                   'error_id': 'Attributes'})
                    counter_warn += 1

            for k, problem_elem in test_radio_disabled_textAlternative.testing_attribute_read(
                    webdriver_instance, button_radiogroups_dict[key]):
                conclusion['checked_elements'].append(problem_elem)
                conclusion['elements'].append({'element': problem_elem,
                                               'problem': 'Error: No label or accompanying text was '
                                                          'found for this radio.',
                                               'error_id': "Attributes"})
                counter_error += 1

    Element.safe_foreach(list(button_radiogroups_dict.keys()), check)
    if counter_error:
        conclusion["status"] = "FAIL"
    elif counter_warn:
        conclusion["status"] = "WARN"
    return conclusion
