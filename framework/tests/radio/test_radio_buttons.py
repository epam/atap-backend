import time
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from lxml import etree
from framework.element_locator import ElementLocator
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, \
                                       ElementNotVisibleException, ElementClickInterceptedException, \
                                       ElementNotInteractableException, WebDriverException, ElementClickInterceptedException
from framework.element import Element, ElementLostException

name = "Test for elements behaving like radiobuttons"
IGNORED_TAGS = ['script', 'style', 'section', 'br', 'table', 'tr', 'hr', 'a', 'p', 'ul']
possible_radio = []
possible_radiogroup = []
possible_radiogroup_ids = []
webdriver_restart_required = True

WCAG = '4.1.2'
framework_version = 0
elements_type = "radio"
test_data = [
    {
        "page_info": {
            "url": "page_good_radio.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_bugs_radio.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 5
    }
]


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):
    """
    done:
    1) checked labels or internal text
    2) the behavior of lika radiobutton was checked for elements not marked as input: aligned with X,
    changes of one radiobutton entail changes in neighbors (the neighbors were considered buttons 
    of a similar structure and visually aligned).

    Restrictions
    1. If in the process of clicking all the elements the page has changed (there was a transition to a new one,
    an alert or a dialog box appeared), then further testing may break.
    2. It is possible to implement horizontal tabs (menu) with which the signs can match. A further possible solution,
    if necessary, is to search for the visual "circle" pattern at the beginning of the active elements.
    3. If the active element is wrapped in many containers and the visual beacon is made using pseudo-elements and is not present in the DOM

    """
    custom_buttons = []
    custom_groups = []
    elements = []
    activity.get(webdriver_instance)
    custom_radio_buttons = find_all_disguised_radio_buttons(webdriver_instance, element_locator)
    for radio_button in custom_radio_buttons:
        if 'type="radio"' not in radio_button['element'].source:
            custom_buttons.append(radio_button['element'])
            if not button_has_attrs(radio_button['outerHTML']):
                elements.append(
                    {"element": radio_button['element']})

    activity.get(webdriver_instance)
    custom_radio_groups = test_radiogroups_by_selenium_ids(
        webdriver_instance, possible_radiogroup)

    radio_groups = list()

    for radio_group in custom_radio_groups:
        if 'type="radio"' not in radio_group['element'].source:
            custom_groups.append({'element': radio_group['element'], 'radio_buttons': radio_group['radio_buttons'], 'has_correct_navigation': radio_group['has_correct_navigation']})
            radio_groups.append(radio_group)
            if not group_has_attrs(radio_group['outerHTML']):
                elements.append(
                    {"element": radio_group['element']})

    checked_elements = custom_buttons 
    result = ''
    if len(elements) > 0:
        result = 'Some problems with radiobuttons found'
        status = "FAIL"
    else:
        result = 'Problems with radiobuttons not found'
        status = "PASS"

    return {
        "status": status,
        "message": result,
        "elements": elements,
        "radio": custom_buttons,
        "radiogroups": custom_groups,
        "checked_elements": checked_elements
    }


def test_radiogroups_by_selenium_ids(webdriver_instance, possible_radiogroup):
    # for looking radiogroup after page's reload
    finded_elements = []
    #elements = webdriver_instance.find_elements_by_xpath('/html/body//*')
    counter = 0
    for element in possible_radiogroup:
        counter += 1
        print(f"\rTesting all radio groups {counter}/{len(possible_radiogroup)}", end="", flush=True)
        el = element['element'].get_element(webdriver_instance)
        test_up_down, children = test_up_down_btn(webdriver_instance, el)
        finded_elements.append({'outerHTML': get_element_as_string(
            el), 'has_correct_navigation': test_up_down,
            'radio_buttons': children,
            'element':  Element(el, webdriver_instance)})
    return finded_elements


def get_all_attr_as_dict(outerHTML):
    # get all attributes from outerHTML (string)
    tree = etree.fromstring(outerHTML)
    return dict(tree.attrib)


def find_all_disguised_radio_buttons(webdriver_instance, element_locator):
    # find radio buttons in all existing elements
    count = 0
    def check_interactive(element):
        nonlocal count
        count += 1
        print(f"\rTesting all elements to find radio buttons {count}/{len(clickables)}", end="", flush=True)
        try:
            if element.get_parent(webdriver_instance).tag_name != 'a':
                element_selenium = element.get_element(webdriver_instance)
                neighbors = get_all_neighbors_without_element(element_selenium)
                neighbors_html_start = get_neighbors_html(neighbors)
                start_state = element_selenium.get_attribute('outerHTML')
                start_height = element_selenium.size['height']
                if (start_height > 3 and neighbors and start_height < 100 and element_selenium.size['width'] + 20 < webdriver_instance.execute_script("return window.innerWidth")):
                    element.click(webdriver_instance)
                    time.sleep(0.2)
                    neighbors = get_all_neighbors_without_element(element_selenium)
                    neighbors_html_end = get_neighbors_html(neighbors)
                    end_state = element_selenium.get_attribute('outerHTML')
                    element.click(webdriver_instance)
                    time.sleep(0.2)
                    revert_state = element_selenium.get_attribute('outerHTML')
                    neighbors = get_all_neighbors_without_element(element_selenium)
                    if (bom_is_changed(start_state, end_state)) and \
                        not bom_is_changed(end_state, revert_state) and \
                            width_not_changed(start_height, element_selenium.size['height']):
                        if neighbors_was_changed(neighbors_html_start, neighbors_html_end):
                            if len(neighbors) > 0:
                                parent = element_selenium.find_element_by_xpath('..')
                                parent_id = re.search(r'(?<=-)\d+', str(parent.id))
                                parent_id = parent_id.group(0)
                                radio_obj = {'outerHTML': start_state,
                                            'parent': parent,
                                            'el_id': element_selenium.get_attribute('id'), 'element': element}
                                parent_obj = {'outerHTML': get_element_as_string(
                                    parent), 'has_correct_navigation': False, 'element': Element(parent, webdriver_instance)}
                                possible_radio.append(radio_obj)
                                if neighbors_html_start[-1] != neighbors_html_end[-1] and outerhtml_elements_are_similar(neighbors_html_end[-1], start_state):
                                    radio_first_obj = {
                                        'outerHTML': neighbors_html_end[-1], 'parent': parent, 'element': Element(neighbors[-1], webdriver_instance)}
                                    if radio_first_obj not in possible_radio:
                                        possible_radio.append(radio_first_obj)
                                if parent_id not in possible_radiogroup_ids:
                                    possible_radiogroup_ids.append(parent_id)
                                    possible_radiogroup.append(parent_obj)
        except (StaleElementReferenceException, ElementNotVisibleException,
                NoSuchElementException, ElementClickInterceptedException,
                ElementNotInteractableException, WebDriverException, ElementClickInterceptedException):
            pass
    #elements = webdriver_instance.find_elements_by_xpath('/html/body//*')
    native_radio_buttons = webdriver_instance.find_elements_by_xpath(
        '//input[@type="radio"]')
    clickables = list(filter(lambda x: x.tag_name != "a", element_locator.get_activatable_elements(element_types=['button', 'div', 'span', 'label', 'input'])))
    print(len(clickables))
    Element.safe_foreach(clickables, check_interactive) 
    return possible_radio


def bom_is_changed(start_state, end_state):
    # very simple checking that DOM was changed
    return (start_state != end_state)


def element_is_changed(start_state, end_state):
    # very simple checking that element was changed
    return (start_state != end_state)


def save_current_BOM(webdriver_instance):
    # save current DOM to string
    source = webdriver_instance.page_source
    source = clear_BOM(str(source))
    return source


def get_neighbors_html(elements):
    # get outerHTML of some elements
    neig = []
    for el in elements:
        neig.append(get_element_as_string(el))
    return neig


def neighbors_was_changed(elements_html_start, elements_html_end):
    # very simple checking that elements was changed (spaces was deleted by r'\s+', ' ')
    changed = False
    if len(elements_html_start) != len(elements_html_end):
        changed = False
    else:
        for i in range(len(elements_html_start)):
            elements_html_start[i] = re.sub(
                r'\s+', ' ', elements_html_start[i])
            elements_html_end[i] = re.sub(r'\s+', ' ', elements_html_end[i])
            if elements_html_start[i] != elements_html_end[i]:
                changed = True
    return changed


def button_has_attrs(element_html):
    # cheking that custom radiobutton has necessary attributes
    return ('role="radio"' in element_html and ('aria-checked=' in element_html))


def group_has_attrs(element):
    # cheking that custom radiogropu has necessary attributes
    return element.find('role="radiogroup"') != -1


def elements_has_visual_order_evenly(elements):
    # checking that elements has visual order (It needs some work!!!)
    if len(elements) == 0:
        return False
    has_visual_order = True
    elements_heights = []
    elements_top_left = []
    for el in elements:
        elements_heights.append(el.size['height'])
        elements_top_left.append(el.location['y'])
    prev_elem_botom_left = elements_heights[0] + elements_top_left[0]
    for i in range(1, len(elements_heights), 1):
        if prev_elem_botom_left < elements_top_left[i]:
            has_visual_order = False
            break
    return has_visual_order


def get_all_neighbors(element):
    # get all neighbors
    parent = element.find_element_by_xpath('..')
    all_children_by_xpath = parent.find_elements_by_xpath(".//*")
    return(all_children_by_xpath)


def element_have_size(element):
    # checking that element has size more than 1x1 px
    if element.size['height'] <= 1 or element.size['width'] <= 1:
        return False
    else:
        return True


def get_all_neighbors_without_element(element):
    # get all SIMILAR neighbors, excluding element
    parent = element.find_element_by_xpath('..')
    all_children_by_xpath = parent.find_elements_by_xpath("*")
    all_children_by_xpath.remove(element)

    for child in all_children_by_xpath:
        if not element_have_size(child):
            all_children_by_xpath.remove(child)

    for child in all_children_by_xpath:
        if (child.location['y'] == element.location['y']):
            all_children_by_xpath.remove(child)

    for child in all_children_by_xpath:
        if (child.location['x'] != element.location['x']):
            all_children_by_xpath.remove(child)

    for child in all_children_by_xpath:
        if (child.location['x'] == 0):
            all_children_by_xpath.remove(child)

    for child in all_children_by_xpath:
        if (child.tag_name != element.tag_name) or \
           (child.tag_name in IGNORED_TAGS):
            all_children_by_xpath.remove(child)
    return(all_children_by_xpath)


def get_element_as_string(element):
    # get outerHTML of element
    return element.get_attribute('outerHTML')


def element_in_possible_radio(el):
    flag = False
    for btn in possible_radio:
        if outerhtml_elements_are_similar(btn['outerHTML'], get_element_as_string(el)):
            flag = True
    return flag


def get_widths(elements):
    widths = []
    for el in elements:
        widths.append(el.size['width'])
    return width


def width_not_changed(element_width_start, element_width_end):
    return element_width_start == element_width_end


def outerhtml_elements_are_similar(element1, element2):
    similar = False
    try:
        el_1 = etree.fromstring(element1)
        el_2 = etree.fromstring(element2)
        if el_1.tag == el_2.tag:
            classes_1 = str(el_1.get('class')).split()
            classes_2 = str(el_2.get('class')).split()
            common_classes = list(set(classes_1).intersection(classes_2))
            if len(common_classes) > 0 or (el_1.get('role') == el_2.get('role') and len(el_1.get('role')) > 0) or (el_1.get('name') == el_2.get('name') and len(el_1.get('name')) > 0):
                similar = True
    except:
        pass
    return similar


def test_up_down_btn(webdriver_instance, radio_group):
    # check that radiogroup has correct keyboard control
    navigation_working = True
    all_children = radio_group.find_elements_by_xpath(".//*")
    for child in all_children:
        if not element_in_possible_radio(child):
            all_children.remove(child)
    all_children_framework = [Element(el, webdriver_instance) for el in all_children]
    if all_children:
        try:
            all_children[0].click()
            time.sleep(0.5)
            for i in range(1, len(all_children)):
                elem = webdriver_instance.switch_to.active_element
                elem.send_keys(Keys.DOWN)
                time.sleep(0.2)
                elem = webdriver_instance.switch_to.active_element
                if elem != all_children[i]:
                    navigation_working = False
                    break
            for i in range(len(all_children)-1, 0):
                elem = webdriver_instance.switch_to.active_element
                elem.send_keys(Keys.UP)
                time.sleep(0.2)
                elem = webdriver_instance.switch_to.active_element
                if elem != all_children[i]:
                    navigation_working = False
                    break
        except (ElementNotVisibleException, ElementClickInterceptedException):
            pass
    for child in all_children_framework:
        if child.source == '<br>':
            all_children_framework.remove(child)
    return navigation_working, all_children
