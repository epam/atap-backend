from collections import defaultdict
from selenium import webdriver

from framework.element_locator import ElementLocator
from framework.element import Element


depends = ["test_radio_buttons"]
webdriver_restart_required = True
framework_version = 5
WCAG = '1.1.1'
elements_type = "radio"
test_data = [
    {
        "page_info": {
            "url": "radio_disabled/page_bugs_radio_disabled_2.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "radio_disabled/page_good_radio_disabled.html"
        },
        "expected_status": "PASS"
    },
]

name = "Ensures that icons next to the disabled radio buttons have text description "
NUMBER_OF_ATTEMPTS = 10


def get_all_attributes(driver, element) -> dict:
    return driver.execute_script('var items = {}; for (index = 0; index < arguments[0].attributes.length; ++index) { '
                                 'items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value }; '
                                 'return items;', element.get_element(driver))


def get_pseudo_before_element(driver, element):
    return driver.execute_script("return window.getComputedStyle(arguments[0], ':before')." +
                                 "getPropertyValue('content');", element.get_element(driver))


def get_pseudo_after_element(driver, element):
    return driver.execute_script("return window.getComputedStyle(arguments[0], ':after')." +
                                 "getPropertyValue('content');", element.get_element(driver))


def get_parent_with_multiple_children_input(driver, element):
    parent = element.get_parent(driver)
    if parent is None:
        return None
    while len(parent.find_by_xpath("descendant::input", driver)) < 2:
        parent = parent.get_parent(driver)
        if parent is None:
            return None
    return parent


def get_parent_with_children(driver, element):
    parent = element.get_parent(driver)
    if parent is None:
        return None
    while len(parent.find_by_xpath("child::*", driver)) < 2:
        parent = parent.get_parent(driver)
        if parent is None:
            return None
    return parent


def check_link_that_button(driver, elem):
    return elem.click(driver)['action'] == 'NONE' or\
           [attr for attr in list(get_all_attributes(driver, elem).values()) if attr.find('button') != -1
            or attr.find('submit') != -1] or elem.get_attribute(driver, "href") == '#'


def find_button(driver, radiogroup):
    container_element = radiogroup['element']
    for i in range(3):
        descendants = container_element.find_by_xpath("descendant::*", driver)
        for elem in descendants:
            if elem.tag_name == 'button' or \
                    (elem.tag_name == 'input' and (elem.get_attribute(driver, "type") == 'submit'
                                                   or elem.get_attribute(driver, "type") == 'button')) \
                    or (elem.tag_name == 'a' and check_link_that_button(driver, elem)):
                return elem
        container_element = get_parent_with_children(driver, container_element)
        if container_element is None:
            return None
    return None


def get_children(driver, parent):
    return parent.find_by_xpath("child::*", driver)


def get_standard_radiogroups(driver, element_locator, radiogroups):
    elements = [elem for elem in element_locator.get_all_of_type(driver, element_types=['input'])
                if elem.get_attribute(driver, "type") == 'radio']
    standard_radiogroups = defaultdict(list)
    for e in elements:
        parent = get_parent_with_multiple_children_input(driver, e)
        if parent is None:
            continue
        standard_radiogroups[(e.get_attribute(driver, "name"), parent)].append(e)
    for key, values in standard_radiogroups.items():
        radiogroups.append({'element': key[1],
                            'radio_buttons': values})


def activate_radio(driver, radiogroups):
    for radio in radiogroups:
        if isinstance(radio['radio_buttons'][0], Element):
            event = radio['radio_buttons'][0].click(driver)
        else:
            return False
        if event['action'] == "NONINTERACTABLE":
            return False
    return True


def activate_button(driver, button):
    event = button.click(driver)
    return event, event['action'] != "NONINTERACTABLE"


def check_feedback_on_presence_of_try_again(driver, radiogroups):
    """support only text feedback"""
    for radiogroup in radiogroups:
        container_element = radiogroup['element']
        for i in range(2):
            descendants = [elem for elem in container_element.find_by_xpath("descendant::*", driver) if
                           elem not in radiogroup['radio_buttons']]
            for descendant in descendants:
                if descendant.get_text(driver).lower().find('try again') != -1:
                    return True
            container_element = get_parent_with_children(driver, container_element)
            if container_element is None:
                return False
    return False


def event_handing(driver, event, radiogroups, button):
    if event['action'] == 'NONE':
        counter = 0
        # if 'try again' -> press radios and 'submit' button again
        while counter < NUMBER_OF_ATTEMPTS and check_feedback_on_presence_of_try_again(driver, radiogroups):
            flag = activate_radio(driver, radiogroups)
            if not flag:
                return False
            _, flag = activate_button(driver, button)
            if not flag:
                return False
            counter += 1
        return True
    return False


def check_attribute_checked(driver, radio):
    children = get_children(driver, radio)
    if not children:
        attributes = get_all_attributes(driver, radio)
        if 'checked' in attributes.keys():
            return True
        if 'aria-checked' in attributes.keys() and attributes['aria-checked'] == 'true':
            return True
    else:
        for child in children:
            attributes = get_all_attributes(driver, child)
            if 'checked' in attributes.keys():
                return True
            if 'aria-checked' in attributes.keys() and attributes['aria-checked'] == 'true':
                return True
    return False


def find_label_for_radio(driver, container_element, radio):
    """ label = correct/incorrect """

    children = get_children(driver, radio)
    elem_id = [id for id in [radio.get_attribute(driver, "id")] if id]
    list_aria_labelledby = [aria.split(' ') for aria in [radio.get_attribute(driver, "aria-labelledby")] if aria]
    if children:
        elem_id.extend([child.get_attribute(driver, "id") for child in children if child.get_attribute(driver, "id")])
        list_aria_labelledby.extend([elem.get_attribute(driver, "aria-labelledby").split(' ') for elem in children if
                                     elem.get_attribute(driver, "aria-labelledby")])

    descendants = container_element.find_by_xpath("descendant::*", driver)
    for des in descendants:
        id_des = des.get_attribute(driver, "id")
        if id_des:
            for aria in list_aria_labelledby:
                if id_des in aria:
                    return des
        des_for = des.get_attribute(driver, "for").split(' ') if des.get_attribute(driver, "for") else []
        if des_for:
            for id in elem_id:
                if id in des_for:
                    return des


def testing_attribute_read(driver, radiogroups):
    """if radiobutton have attribute\background element 'corrent'\'incorrect', it should be read """

    problem_radios = list()
    for radiogroup in radiogroups:
        for radio in radiogroup['radio_buttons']:
            if get_pseudo_before_element(driver, radio) != 'none' or get_pseudo_after_element(driver, radio) != 'none' \
                    or check_attribute_checked(driver, radio):
                label = find_label_for_radio(driver, radiogroup['element'], radio)
                if label is None:
                    problem_radios.append((None, radio))
                    continue
                # not .text, because may be <span>
                html_text = label.source
                if html_text.lower().find('correct') == -1:
                    problem_radios.append((1, radio))
    return problem_radios


def get_button_and_radiogroups_dict(driver, buttons, button_radiogroups_dict, radiogroups):
    for radio in radiogroups:
        button = find_button(driver, radio)
        if button is None:
            # ignore
            continue
        if button in buttons:
            button_radiogroups_dict[buttons.index(button)].append(radio)
        else:
            buttons.append(button)
            button_radiogroups_dict[len(buttons) - 1].append(radio)
    return buttons, button_radiogroups_dict


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)
    conclusion = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': []}
    radiogroups = dependencies["test_radio_buttons"]["radiogroups"]

    get_standard_radiogroups(webdriver_instance, element_locator, radiogroups)
    if not radiogroups:
        conclusion['status'] = 'NOELEMENTS'
        return conclusion

    buttons, button_radiogroups_dict = get_button_and_radiogroups_dict(webdriver_instance, list(),
                                                                       defaultdict(list), radiogroups)
    counter = 1

    def check(key):
        nonlocal counter
        print(f'\rAnalyzing radiogroups {counter}/{len(button_radiogroups_dict)}', end="", flush=True)
        counter += 1
        if not activate_radio(webdriver_instance, button_radiogroups_dict[key]):
            # radio-s are not clickable
            return
        event, flag = activate_button(webdriver_instance, buttons[key])
        if flag and event_handing(webdriver_instance, event, button_radiogroups_dict[key], buttons[key]):
            for k, problem_elem in testing_attribute_read(webdriver_instance, button_radiogroups_dict[key]):
                conclusion['checked_elements'].append(problem_elem)
                if k is not None:
                    conclusion['elements'].append({'element': problem_elem,
                                                   'problem': "The radio probably had a correct/incorrect icon "
                                                              "next to it, but it wasn't read out.",
                                                   'error_id': "TextAlternative"})
    Element.safe_foreach(list(button_radiogroups_dict.keys()), check)
    if conclusion['elements']:
        conclusion["status"] = "FAIL"
    return conclusion
