import time
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from framework.element import Element
from framework.element_locator import ElementLocator
from framework.screenshot.screenshot import Screenshot
from framework.libs.is_visible import is_visible

STOP_WORDS = ['menu']


class ModalFinder:
    def __init__(self, driver: webdriver.Firefox, locator: ElementLocator, activity):
        self._dr: webdriver.Firefox = driver
        self._loc: ElementLocator = locator
        self.checked_backprops = []
        self.activity = activity
        self.activators = []
        self.modals = dict()
        self.ignored_elements = set()

    def add_screenshot(self, screenshot_id, element, activator):
        self.activity.get(self._dr)
        activator.click(self._dr)
        time.sleep(0.2)
        print(f"\rTaking screenshot {screenshot_id}...", end="", flush=True)
        screenshot_filename = f"screenshots/img{screenshot_id}.png"
        img = Screenshot(self._dr, element['element']).single_element()
        if img is not None:
            element["screenshot"] = screenshot_filename
            width, height = img.size
            element["screenshot_height"] = height
            element["screenshot_width"] = width
            img.save(screenshot_filename)
        return element

    def clickable_is_valid(self, clickable: Element):
        return (clickable.get_element(self._dr).size['width'] > 20
                and clickable.get_element(self._dr).size['height'] > 5
                and all(word not in clickable.source for word in STOP_WORDS))

    def find_ignored_elements(self):
        start = time.time()
        visible_divs = [e for e in self._loc.get_all_by_xpath(
            self._dr, "//body//descendant::div") if is_visible(e, self._dr)]
        while time.time() - start <= 10:
            current_visible_divs = [e for e in self._loc.get_all_by_xpath(
                    self._dr, "//body//descendant::div") if is_visible(e, self._dr)]
            for div in current_visible_divs:
                if div not in visible_divs:
                    self.ignored_elements.add(div)
            visible_divs = current_visible_divs

    def get_all_activators(self):
        self.find_ignored_elements()
        clickables = self._loc.get_all_by_xpath(
            self._dr,
            "//body//descendant::*[self::a or self::button or self::div[@role='button'] or self::span[@role='button']]"
        )
        counter = 0

        def check_is_modal(clickable: Element):
            nonlocal counter
            counter += 1
            print(f"\rTesting {counter}/{len(clickables)}", end="", flush=True)
            if not is_visible(clickable, self._dr) or not self.clickable_is_valid(clickable):
                return
            visible_div_before_click = [e for e in self._loc.get_all_by_xpath(self._dr, "//body//descendant::div")
                                        if is_visible(e, self._dr) and e not in self.ignored_elements]
            try:
                self._loc.activate_element(clickable)
                click_result = clickable.click(self._dr)
            except WebDriverException:
                self.activity.get(self._dr)
                return
            if click_result['action'] not in ['NONE', 'NONINTERACTABLE']:
                return
            if click_result['action'] == 'NONINTERACTABLE':
                self._dr.execute_script("arguments[0].click();", clickable.get_element(self._dr))
                time.sleep(1.5)

            modal = self.get_modal_on_page(visible_div_before_click)
            if modal:
                self.activators.append(clickable)
                self.modals[clickable] = modal
                self.activity.get(self._dr)
        Element.safe_foreach(clickables, check_is_modal)
        return self.activators

    def get_modal_on_page(self, visible_elements_before_click):
        elements = []
        body = self._loc.get_all_of_type(self._dr, element_types=['body'])[0]
        backdrop = self.find_backdrop(body)
        if backdrop is not None:
            child: Element
            for child in backdrop.find_by_xpath("descendant::*", self._dr):
                if child == backdrop or child in self.ignored_elements:
                    continue
                if child.tag_name not in ['a', 'button'] and is_visible(child, self._dr) and self.position_like_modal_dialog(child):
                    elements.append(child)
                    break
            if not elements:
                visible_div = [e for e in self._loc.get_all_by_xpath(
                    self._dr, "//body//descendant::div") if is_visible(e, self._dr) and e not in self.ignored_elements]
                for div in visible_div:
                    if div != backdrop and div not in visible_elements_before_click and self.position_like_modal_dialog(div):
                        elements.append(div)
                        break
        return elements

    def position_like_modal_dialog(self, element: Element):
        # innerHeight = driver.execute_script("return window.innerHeight")
        # innerWidth = driver.execute_script("return window.innerWidth")
        selenium_element = element.get_element(self._dr)
        return ((selenium_element.location['x'] > 10 or selenium_element.location['y'] > 10)
                and selenium_element.size['width'] > 70 and selenium_element.size['height'] > 70)

    def find_backdrop(self, body: Element):
        body_children = body.find_by_xpath("descendant::div", self._dr)
        if body_children:
            child: Element
            for child in body_children:
                selenium_element = child.get_element(self._dr)
                if selenium_element.get_attribute('outerHTML') not in self.checked_backprops:
                    if selenium_element.size['height'] >= 200 and selenium_element.location['x'] >= 0 and self.is_backdrop(child):
                        return child
                    self.checked_backprops.append(selenium_element.get_attribute('outerHTML'))
        return None

    def is_backdrop(self, element: Element):
        css_attr = {'position': '', 'top': '', 'right': '', 'left': '', 'width': '', 'height': '', 'bottom': ''}
        selenium_element = element.get_element(self._dr)
        for attr in css_attr.keys():
            css_attr[attr] = selenium_element.value_of_css_property(attr)
        if css_attr['position'] == 'fixed':
            if css_attr['top'] == '0px' and css_attr['right'] == '0px' and css_attr['left'] == '0px' and css_attr['bottom'] == '0px':
                return True
        else:
            self.checked_backprops.append(selenium_element.get_attribute('outerHTML'))
            return False

# def check_that_element_has_modal( element, webdriver_instance  ):
#     that_element_has_modal = False
#     body = webdriver_instance.find_element_by_xpath('//body')
#     top_element = find_top_element(body, webdriver_instance)
#     if top_element:
#         if top_element == element:
#             if is_backdrop(top_element, webdriver_instance):
#                 child = top_element.find_elements_by_xpath(".//*")[0]
#                 if position_like_modal_dialog(child, webdriver_instance):
#                     that_element_has_modal = True
#     return that_element_has_modal
#
#
# def preprocess_z_index(z_index):
#     # convert to Int
#     if z_index == 'auto':
#         z_index = 0
#     return int(z_index)
