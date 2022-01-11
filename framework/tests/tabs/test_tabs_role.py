import time
from math import isclose
from collections import defaultdict
from typing import List, Set
from math import inf
from urllib.parse import urlparse, ParseResult

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from framework.element import Element
from framework.element_locator import ElementLocator
from framework.activity import Activity
from framework.libs.hide_cookie_popup import hide_cookie_popup
from framework.libs.advanced_click import advanced_link_click
from framework.libs.distance_between_elements import distance
from framework.libs.is_visible import is_visible
from framework.element_wrapper import ElementWrapper
from framework.tests.tabs.lib import get_common_ancestor

'''
Now only the tablist (the toggle buttons themselves) is detected through, firstly, 
the location (horizontal and vertical), and secondly, the behavior (when you click on one, the buttons change)

MAIN TODO: detect not only the tablist, but also the specific selector of the tab panel.
ErrorID: Each content panel must have a role = ”tabpanel”

Also, new examples for testing were received from Anastasia (not in the document):
https://www.intel.com/content/www/us/en/products/devices-systems/workstations.html 
https://www.airbnb.com/ 
https://www.airbus.com/helicopters.html 
https://developer.ibm.com/components/kubernetes/  
http://www.kikatech.com/  
https://www.lenovo.com/ru/ru/pc/?ipromoID=ftv_espot1_PC  

'''


name = "Test for checking tabs"

IGNORED_TAGS = ['script', 'style', 'section', 'br']
CHECKED_TAGS = ['label', 'div', 'li', 'a', 'button']
CHECKED_ATTRIBUTES = ['class', 'aria-selected', 'tabindex', 'hidden', 'aria-expanded', 'href']
HEADERS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
WCAG = '4.1.2'
framework_version = 4
webdriver_restart_required = True
elements_type = "tabpanel"
test_data = [
    {
        "page_info": {
            "url": "tabs/page_good_tabs.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tabs/page_bugs_tabs.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    }
]


def load_page(driver: webdriver.Firefox, activity: Activity):
    activity.get(driver)
    hide_cookie_popup(driver, activity)
    time.sleep(10)


def scroll(driver: webdriver.Firefox, element):
    # scroll to element
    if isinstance(element, Element):
        element = element.get_element(driver)
    driver.execute_script(f"window.scrollTo(0, {element.location['y'] - 0.5 * driver.get_window_size()['height']})")
    time.sleep(1)


def find_elements(driver: webdriver.Firefox, ancestor: Element, element: Element, ignored_element):
    def check_location(elem_1: Element, elem_2: Element) -> bool:
        el_1 = elem_1.get_element(driver)
        el_2 = elem_2.get_element(driver)
        return el_1.location['x'] - 15 <= el_2.location['x'] and el_1.location['y'] <= el_2.location['y']

    return [e for e in ancestor.find_by_xpath("descendant::*", driver) if
            all(i > 5 for i in e.safe_operation_wrapper(lambda x: x.get_element(driver).size.values(), on_lost=lambda: [0]))
            and distance(driver, e, element) < 600 and check_location(element, e) and e not in ignored_element]


def find_changed_elements(driver: webdriver.Firefox, status_before_click, current_status):
    changed_elements = set()
    for element in status_before_click:
        if (element not in current_status or status_before_click[element] != current_status[element]
                or status_before_click[element].html != current_status[element].html):
            changed_elements.add(element)
    descendants = sum([i.safe_operation_wrapper(lambda e: e.find_by_xpath("descendant::*", driver), on_lost=lambda: [])
                       for i in changed_elements], [])
    return {i for i in changed_elements if i not in descendants}


def get_states(driver, elements):
    states = dict()

    def check(e):
        states[e] = State(driver, e)
    Element.safe_foreach(elements, check)
    return states


def find_tab_panels(driver: webdriver.Firefox, tab_groups, ignored_elements: Set[Element]):
    tab_panels = dict()
    for parent, tabs in tab_groups.items():
        if not tabs:
            tabs = parent.find_by_xpath('child::*', driver)
        ancestors = [a for a in parent.safe_operation_wrapper(
            lambda x: x.find_by_xpath('ancestor::*', driver), on_lost=lambda: []) if a.tag_name != 'html'][::-1]
        if not ancestors:
            continue
        ancestor = ancestors[3] if len(ancestors) > 3 else ancestors[-1]
        changed_elements = set()
        ignored_elements_ = ignored_elements | set(sum([tab.find_by_xpath("descendant-or-self::*", driver) for tab in tabs], [])
                                                   + [parent] + ancestors
                                                   + sum([tab.find_by_xpath("parent::*", driver) for tab in tabs], []))
        elements = find_elements(driver, ancestor, parent, ignored_elements_)
        for tab in tabs:
            state = State(driver, tab)
            if state.input_state is not None:
                state = state.input_state
            if (any(i in " ".join(str(x) for x in state.attributes.values()) for i in ['selected', 'active', 'current'])
                    and state.attributes['aria-selected'] == 'true'):
                continue
            before_click_status = get_states(driver, elements)
            if not click(driver, tab):
                continue
            current_status = get_states(driver, elements)
            changed_elements |= find_changed_elements(driver, before_click_status, current_status)
        tab_panel = sorted(filter_tabs(driver, changed_elements), key=lambda x: distance(driver, parent, x))
        if tab_panel:
            tab_panels[parent] = [tab_panel[0]]
    return tab_panels


def check_link(driver: webdriver.Firefox, activity_link: ParseResult, link):
    source = link.source if isinstance(link, Element) else link.get_attribute('outerHTML')
    href = link.get_attribute(driver, 'href') if isinstance(link, Element) else link.get_attribute('href')
    parsed_url = urlparse(href)
    return (not link.tag_name == 'a' or all(s not in source for s in ['href="http', 'href="/'])
            or parsed_url.netloc == activity_link.netloc)


def find_clickable_elements(state, neighbor_states):
    elem = state.framework_element
    if state.input_state is not None:
        state = state.input_state
    if (all(i not in " ".join(str(i) for i in state.attributes.values()) for i in ['selected', 'active', 'current'])
            and state.attributes['aria-selected'] in ['false', None]):
        return [elem]
    else:
        neighbor: State
        elements = []
        for elem, neighbor in neighbor_states.items():
            if neighbor.input_state is not None:
                neighbor = neighbor.input_state
            if (all(i not in " ".join(str(i) for i in neighbor.attributes.values()) for i in ['selected', 'active'])
                    and neighbor.attributes['aria-selected'] in ['false', None]):
                elements.append(elem)
        return elements


def click(driver, element):
    res = advanced_link_click(element, driver)
    if res['action'] == 'INTERNALLINK' and element.tag_name == 'a':
        element.get_element(driver).click()
        time.sleep(2)
        return True
    if res['action'] == 'NONINTERACTABLE':
        scroll(driver, element)
        time.sleep(2)
        res = advanced_link_click(element, driver)
    return res['action'] == 'NONE'


def find_tabs(driver: webdriver.Firefox, activity: Activity, result: dict, clickable_elements: List[Element],
              ignored_elements: Set[Element]):
    counter = 0

    tabs = defaultdict(list)
    activity_link = urlparse(activity.url)

    def check_tab(tab: Element, wrap: ElementWrapper):
        h, w = wrap.size
        return (tab not in ignored_elements and wrap.is_visible and h < 100 and w > 5 and wrap.text.strip()
                and len(wrap.text.strip()) > 2 and 'slider' not in tab.get_parent(driver).source.lower()
                and (('<input' in tab.source.lower() and tab.tag_name == 'label')
                     or all(s not in tab.source.lower() for s in ['dropdown', '<script', 'slider', '<style>', '<img', '<svg', '<i']))
                and check_link(driver, activity_link, wrap.framework_element))

    def is_tab(element: Element):
        nonlocal counter
        counter += 1
        wrap = ElementWrapper(element, driver)
        if check_tab(element, wrap):
            neighbors = get_all_neighbors_without_element(driver, activity_link, wrap.element, ignored_elements)
            if neighbors:
                element_state_start = State(driver, element)
                neighbors_state_start = get_states(driver, neighbors)
                # using advanced_click for detect tabs with link that change page URL
                # (for relative interfaces, for example, https://www.wiziq.com/)
                clickable_elements = find_clickable_elements(element_state_start, neighbors_state_start)
                if not clickable_elements:
                    return
                if not click(driver, clickable_elements[-1]):
                    return
                element_state_end = State(driver, element)
                neighbors = get_all_neighbors_without_element(driver, activity_link, element.get_element(driver), ignored_elements)
                neighbors_state_end = get_states(driver, neighbors)
                if (element_state_start.compare_location(element_state_end) and element_state_start != element_state_end
                        and neighbors and neighbors_was_changed(neighbors_state_start, neighbors_state_end)):
                    parent = get_common_ancestor(driver, element, neighbors[0])
                    if parent.tag_name in ['body', 'html'] or any(s in parent.source for s in ['dropdown', 'slider']):
                        return
                    result['checked_elements'].extend([parent, element])
                    tabs[parent].append(element)
                load_page(driver, activity)
    Element.safe_foreach(clickable_elements, is_tab)
    for parent, elements in tabs.items():
        elements = filter_tabs(driver, elements)
        elements = [e for e in elements if all(i.selector_no_id == e.selector_no_id or i.tag_name == e.tag_name
                                               or i.selector_no_id not in e.selector_no_id for i in elements)]
        if len(elements) > 1 and all(e.tag_name == elements[0].tag_name for e in elements[1:]):
            result['tab_groups'][parent] = elements


def check_all_roles(parent: Element, group: List[Element], tab_panels: List[Element]):
    return ('role="tablist"' not in parent.source and (not group or any('role="tab"' not in tab.source for tab in group))
            and (tab_panels is None or any('role="tabpanel"' not in tab.source for tab in tab_panels)))


class State:

    def __init__(self, driver: webdriver.Firefox, elem):
        self.dr = driver
        self.element: WebElement = elem.get_element(driver) if isinstance(elem, Element) else elem
        self.framework_element = elem if isinstance(elem, Element) else Element(elem, driver)
        self.tag = self.framework_element.tag_name
        self.html = self.element.get_attribute('outerHTML')
        self.attributes = {attr: self.element.get_attribute(attr) for attr in CHECKED_ATTRIBUTES}
        self.size = self.element.size.values()
        self.location = self.element.location.values()
        self.is_visible = is_visible(self.element, driver)
        self.background_image = self.element.value_of_css_property('background-image')
        # self.background_color = self.element.value_of_css_property('background-color')
        self.z_index = self.element.value_of_css_property('z-index')
        self.input_children = self.element.find_elements_by_xpath('child::input') if elem.tag_name == 'label' else []
        self.input_state = State(driver, self.input_children[0]) if self.input_children else None

    def __repr__(self):
        return f"State(html={self.html}, size={self.size}, is visible={self.is_visible}, " \
               f"attributes={self.attributes}, background-image={self.background_image}, " \
               f"z-index={self.z_index})\n"

    def compare_location(self, other):
        return all(abs(i - j) < 10 for i, j in zip(self.location, other.location))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.attributes == other.attributes and all(isclose(i, j) for i, j in zip(self.size, other.size))
                    and self.background_image == other.background_image and self.is_visible == other.is_visible
                    and self.z_index == other.z_index and self.input_state == other.input_state)
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (self.attributes != other.attributes or any(not isclose(i, j) for i, j in zip(self.size, other.size))
                    or self.background_image != other.background_image or self.is_visible != other.is_visible
                    or self.z_index != other.z_index or self.input_state != other.input_state)
        else:
            return True


def find_common_ancestor_for_group(driver: webdriver.Firefox, elements: List[Element]) -> (Element, None):
    if not elements:
        return None
    common_ancestor = elements[0]
    for elem in elements[1:]:
        common_ancestor = get_common_ancestor(driver, elem, common_ancestor, or_self=True)
        if common_ancestor is None:
            return common_ancestor
    return common_ancestor


def find_container(driver: webdriver.Firefox, element: Element, other_elements: List[Element]):
    common_ancestor = find_common_ancestor_for_group(driver, other_elements + [element])
    if common_ancestor is None or common_ancestor.tag_name in ['html', 'body']:
        return None
    elements_in_container = other_elements + element.find_by_xpath('ancestor-or-self::*', driver)
    children = [x for x in common_ancestor.find_by_xpath('child::*', driver) if is_visible(x, driver)
                and x.tag_name not in HEADERS + ['p']]
    return common_ancestor if abs(sum(child in elements_in_container for child in children) - len(children)) < 3 else None


def filter_tabs(driver, elements):
    descendants = sum([e.safe_operation_wrapper(lambda x: x.find_by_xpath('descendant::*', driver), on_lost=lambda: [])
                       for e in elements ], [])
    return [e for e in elements if e not in descendants]


def create_tab_index_error(element: Element):
    return {
        'element': element,
        'problem': '2.1.1 Tabs implemented without native interactive elements (<button> or <a href=””>) '
                   'must have tabindex=”0”.',
        'error_id': 'tabsTabindex'
    }


def get_changed_elements(driver: webdriver.Firefox):
    changed_elements = set()
    start_time = time.time()
    previous = None
    counter = 0
    body = driver.find_element_by_tag_name('body').find_elements_by_xpath('descendant::*')
    while time.time() < start_time + 300 and counter < 5:
        counter += 1
        replica = {el: el.get_attribute('outerHTML') for el in body if is_visible(el, driver)}
        if previous is not None:
            changed_elements.update([Element(k, driver) for k, v in replica.items() if k not in previous or v != previous[k]])
        previous = replica
    return changed_elements


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    result = {'status': 'PASS', 'message': 'Problems with tabs not found', 'elements': [], 'checked_elements': [],
              'tab_groups': defaultdict(list), 'tab_panels': defaultdict(list), 'elements_without_role': set(),
              'elements_without_tab_index': set()}
    load_page(webdriver_instance, activity)
    ignored_elements = get_changed_elements(webdriver_instance)
    clickable_elements = element_locator.get_all_by_xpath(
        webdriver_instance,
        xpath=f"//body//*[{' or '.join('self::' + s for s in CHECKED_TAGS)}]"
    )
    find_tabs(webdriver_instance, activity, result, clickable_elements, ignored_elements)
    tab_panels = find_tab_panels(webdriver_instance, result['tab_groups'], ignored_elements)
    result['tab_panels'] = tab_panels
    for parent, group in result['tab_groups'].items():
        bad_tabs = []

        def check_tab_index(tab: Element):
            if (tab.tag_name != 'button' and 'tabindex="0"' not in tab.source
                    and (tab.tag_name != 'a' or not tab.get_attribute(webdriver_instance, 'href'))):
                bad_tabs.append(tab)
        Element.safe_foreach(group, check_tab_index)
        if len(bad_tabs) == len(group):
            result['elements'].append(create_tab_index_error(parent))
            result['elements_without_tab_index'].add(parent)
        elif bad_tabs:
            result['elements_without_tab_index'].add(parent)
            for tab in bad_tabs:
                result['elements'].append(create_tab_index_error(tab))

        if check_all_roles(parent, group, result['tab_panels'].get(parent, None)):
            common_ancestor = find_container(webdriver_instance, parent, result['tab_panels'].get(parent, None))
            element = common_ancestor if common_ancestor is not None else parent
            result['elements'].append({
                'element': element,
                'problem': '4.1.2 Element that acts as Tabbed Interface is not implemented accordingly.',
                'error_id': 'allTabRoles'
            })
            result['elements_without_role'].add(parent)
        else:
            if 'role="tablist"' not in parent.source:
                result['elements'].append({
                    'element': parent, 'problem': '4.1.2 Tabbed Interface is implemented incorrectly (tablist).',
                    'error_id': 'tabsRole'})
                result['elements_without_role'].add(parent)
            for tab in group:
                if 'role="tab"' not in tab.source:
                    result['elements'].append({
                        'element': tab, 'problem': '4.1.2 Tabbed Interface is implemented incorrectly (tab).',
                        'error_id': 'tabsRole'})
                    result['elements_without_role'].add(parent)
            if parent in result['tab_panels']:
                for tab_panel in result['tab_panels'].get(parent, []):
                    result['checked_elements'].append(tab_panel)
                    if 'role="tabpanel"' not in tab_panel.source:
                        result['elements'].append({
                            'element': tab_panel,
                            'problem': '4.1.2 Tabbed Interface is implemented incorrectly (tabpanel).',
                            'error_id': 'tabsRole'})
                        result['elements_without_role'].add(parent)

    if result['elements']:
        result['message'] = 'Some problems with tabs found'
        result['status'] = 'FAIL'
    print(result)
    for i, r in enumerate(result['elements']):
        print(i + 1, r)
        print(r['element'].source[:500])
        print('----------------------------------------------------------------------------------------------------')
    return result


def neighbors_was_changed(elements_state_start, elements_state_end):
    if len(elements_state_start) != len(elements_state_end):
        return True
    else:
        # elements_html_start = re.sub(r'\s+', ' ', state['html'])
        # elements_html_end = re.sub(r'\s+', ' ', elements_state_end[elem]['html'])
        return any((state != elements_state_end[elem] if elem in elements_state_end else True)
                   for elem, state in elements_state_start.items())


def get_all_neighbors_without_element(driver: webdriver.Firefox, url: ParseResult, element: WebElement,
                                      ignored_elements: Set[Element]):
    if element.size['height'] < 5 or element.size['width'] < 20 or element.tag_name in IGNORED_TAGS:
        return []
    all_children_by_xpath = element.find_element_by_xpath('parent::*').find_element_by_xpath(
        'parent::*').find_elements_by_xpath(f"descendant::*[self::{element.tag_name}]")
    for child in all_children_by_xpath:
        if abs(child.location['y'] - element.location['y']) > 2 and abs(child.location['x'] - element.location['x']) > 2:
            all_children_by_xpath.remove(child)
    for child in all_children_by_xpath:
        if abs(child.size['height'] - element.size['height']) > 10 or abs(child.size['width'] - element.size['width']) > 65:
            all_children_by_xpath.remove(child)
    for child in all_children_by_xpath:
        if not child.text or not is_visible(child, driver):
            all_children_by_xpath.remove(child)
    for child in all_children_by_xpath:
        if (any(i in child.get_attribute('outerHTML') for i in ['dropdown', 'slider', '<style>'])
                and check_link(driver, url, child)):
            all_children_by_xpath.remove(child)
    min_distance = min(distance(driver, element, child) for child in all_children_by_xpath) if all_children_by_xpath else inf
    if element in all_children_by_xpath:
        all_children_by_xpath.remove(element)
    if min_distance < 10:
        elements = [Element(el, driver) for el in all_children_by_xpath]
        return [el for el in elements if el not in ignored_elements]
    else:
        return []
