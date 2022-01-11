import re
import time
import unicodedata
import tempfile
from typing import List

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.color import Color
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains

from framework.element import Element
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.screenshot.screenshot import Screenshot
from framework.tests.contrast.check_contrast import contrast

TIMEOUT = 2.0
EPSILON = 0.105


class FramesContrast:
    def __init__(self, driver: webdriver.Firefox, locator: ElementLocator):
        self._dr: webdriver.Firefox = driver
        self._loc: ElementLocator = locator

    def _wrap(self, el):
        return ElementWrapper(el, self._dr)

    def result(self, action: str):
        """
        :param action: "hover" or "focus"
        :return: result dict
        """
        result = {
            "status": "PASS",
            "message": "This page no problem with contrast",
            "elements": [],
            "checked_elements": [],
            "labels": []
        }

        checked_elements, elements = self.main(action=action)
        if not checked_elements:
            result["status"] = "NOELEMENTS"
            result["message"] = "This page no problem with contrast"
        elif elements:
            result["status"] = "FAIL"
            result["elements"] = elements
            result["message"] = "Page has problems with contrast"
        result['checked_elements'] = checked_elements
        print(result)
        return result

    @staticmethod
    def get_param(text: str, size: float, bold: bool):
        """
        Checks for conditions for contrast.
        Parameters:
            text (str): visible text of web element
            size (float): font size, px
            bold (bool): font weight (True if text is bold)
        Returns:
            int: coefficient for checking contrast.
        """
        if all([unicodedata.category(i) == 'So' for i in text]):
            return 3
        else:
            # because size - px, not point
            return 3 if (size >= 18.66 and bold) or (size >= 24 and not bold) else 4.5

    def focus(self, element: WebElement, timeout: float):
        """
        imitating the focus on an element
        :param element: (WebElement)
        :param timeout: float
        :return: bool ('true' if focus is correct)
        """
        self._dr.execute_script("arguments[0].focus();", element)
        if self._dr.switch_to.active_element != element:
            return False
        time.sleep(timeout)
        return True

    def hover(self, element, timeout):
        """
        imitating the hover on an element
        :param element: (WebElement)
        :param timeout: float
        :return: bool ('true' if hover is correct)
        """
        try:
            ActionChains(self._dr).move_to_element(element).perform()
        except WebDriverException:
            return False
        time.sleep(timeout)
        return True

    def action(self, action: str, element: ElementWrapper, timeout: float = TIMEOUT, with_scroll: bool = True):
        """
        scroll before action, sleep and imitate action('focus' or 'hover')
        :param action: str, 'focus' or 'hover'
        :param element: ElementWrapper
        :param timeout: float
        :param with_scroll: bool, 'true' if need scroll before action
        :return: bool ('true' if the action was performed without errors)
        """
        if with_scroll:
            self._dr.execute_script(
                f"window.scrollTo(0, {list(element.location)[1] - 0.5 * self._dr.get_window_size()['height']})")
            time.sleep(1)
        if action == 'focus':
            return self.focus(element.element, timeout)
        elif action == 'hover':
            return self.hover(element.element, timeout)

    @staticmethod
    def is_image(text: str, element: WebElement):
        """
        checking that the element is an image
        :param text: (str)
        :param element: (WebElement)
        :return: bool
        """
        image_tags = {'img', 'svg'}
        return (element.tag_name in image_tags
                or set([e.tag_name for e in element.find_elements_by_xpath("ancestor::*")]).intersection(image_tags)
                or set([e.tag_name for e in element.find_elements_by_xpath("descendant::*")]).intersection(image_tags)
                or (not element.find_elements_by_xpath('child::*')
                    and element.value_of_css_property("background-image") != 'none')) and not text

    def get_pseudo_element_attribute(self, pseudo: str, element: WebElement, attr: str = 'content') -> str:
        return self._dr.execute_script(
            f"return window.getComputedStyle(arguments[0], ':{pseudo}').getPropertyValue('{attr}');", element)

    def check_severity(self, wrap: ElementWrapper):
        return not wrap.text.strip() and not self.text_is_visible(wrap) and \
               self.get_pseudo_element_attribute("before", wrap.element) not in ['none', '""']

    @staticmethod
    def text_is_visible(wrap: ElementWrapper):
        return wrap.css_property("overflow") != "hidden" or (
                wrap.element.size["height"] > 5 and wrap.element.size["width"] > 5)

    def remove_hover(self, ancestors):
        size = ancestors.pop().get_element(self._dr).size
        try:
            ActionChains(self._dr).move_by_offset(0.6 * size['width'], 0.6 * size['height']).context_click().perform()
        except WebDriverException:
            return False
        time.sleep(TIMEOUT)

    def detect_graphic_object(self, text: str, wrap: ElementWrapper):
        return (text and all([unicodedata.category(i) == 'So' for i in text])) or not self.text_is_visible(
            wrap) or (not text and wrap.framework_element.get_attribute(self._dr, "data-show-all-default") is None)

    def get_children(self, elem: Element):
        return elem.safe_operation_wrapper(lambda e: e.find_by_xpath("child::*", self._dr), on_lost=lambda: [])

    def get_ancestor(self, elem: Element) -> Element:
        ancestor = elem
        while len(self.get_children(ancestor.get_parent(self._dr))) == 1:
            ancestor = ancestor.get_parent(self._dr)
            if ancestor.tag_name in ['button', 'a']:
                return ancestor
        return ancestor if ancestor != elem else ancestor.get_parent(self._dr)

    def filter_bad_elements(self, bad_elements):
        descendants = sum([e['element'].find_by_xpath('descendant::*', self._dr) for e in bad_elements], [])
        return list(filter(lambda x: x['element'] not in descendants, bad_elements))

    def main(self, action):
        bad_elements = {}
        checked_elements = []
        bad_elements_with_gradient = []
        elements = self._loc.get_all_by_xpath(self._dr, "//body//*[not(child::*[normalize-space(text())])]")
        focused_elements = []
        body = self._wrap(self._loc.get_all_by_xpath(self._dr, '//body')[0])
        previous_element = None

        def check_element(element):
            analyzed_element = self._wrap(element)
            text = analyzed_element.text.strip()
            if not analyzed_element.is_visible or self.is_image(text, analyzed_element.element) \
                    or analyzed_element.framework_element in checked_elements:
                return

            nonlocal previous_element
            if previous_element is not None:
                ancestors = set(
                    analyzed_element.framework_element.find_by_xpath('ancestor::*', self._dr)[-3:]).intersection(
                    previous_element.framework_element.find_by_xpath('ancestor::*', self._dr)[-3:]
                )
                if ancestors and action == "focus":
                    self.action(action, body, with_scroll=False)
                elif ancestors:
                    self.remove_hover(ancestors)

            background_color_before_action = self.prepare_background_color(analyzed_element)
            color_before_action = self.prepare_color(
                analyzed_element, [int(x * 255) for x in background_color_before_action[0]])
            if not self.action(action, analyzed_element) and action == 'focus' \
                    and analyzed_element.element.tag_name in ['span', 'p']:
                ancestor = self.get_ancestor(analyzed_element.framework_element)
                if ancestor not in checked_elements:
                    focused_elements.append(ancestor)
                return

            checked_elements.append(element)
            previous_element = analyzed_element
            if text and self.text_is_visible(analyzed_element):
                bold = int(self.get_css(analyzed_element, "font-weight")) >= 700
                size = float(re.search(r"\d+", self.get_css(analyzed_element, 'font-size'))[0])
                param = self.get_param(text, size, bold)
            else:
                param = 3

            color, background_colors = self.get_colors_value(analyzed_element, color_before_action, background_color_before_action)
            if color is None:
                return
            key = (tuple(color), tuple(tuple(i) for i in background_colors))
            if key in bad_elements and len(background_colors) <= 1:
                return

            result, severity = self.check_odds(color, background_colors, param)
            if result and len(background_colors) <= 1:
                file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                Screenshot(self._dr, element).single_element(draw=True).save(file.name)
                bad_elements[key] = self.bad_element(analyzed_element, action, severity, file, text)
                file.close()
            elif result:
                file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                Screenshot(self._dr, element).single_element(draw=True).save(file.name)
                bad_elements_with_gradient.append(self.bad_element(analyzed_element, action, severity, file, text))
                file.close()

        Element.safe_foreach(elements, check_element)
        Element.safe_foreach(focused_elements, check_element)
        return checked_elements, self.filter_bad_elements(bad_elements_with_gradient + list(bad_elements.values()))

    def bad_element(self, analyzed_element, action, severity, file, text):
        return {
            "element": analyzed_element.framework_element,
            "problem": "Bad contrast",
            "severity": "WARN" if severity or self.check_severity(analyzed_element) else "FAIL",
            "screenshot": file.name,
            "error_id": f"ObjectContrast{action.capitalize()}" if self.detect_graphic_object(text, analyzed_element)
                        else f"test_contrast_{action}"
        }

    @staticmethod
    def check_odds(color, background_colors, odd):
        # if len(background_colors) > 1 => this is gradient background
        _contrast = min([contrast(color, i) for i in background_colors])
        return (_contrast < odd or abs(_contrast - odd) < EPSILON, len(background_colors) > 1
                or (_contrast >= odd and abs(_contrast - odd) < EPSILON))

    def get_colors_value(self, analyzed_element, color_before, background_color_before):
        background_colors = self.prepare_background_color(analyzed_element)
        color = self.prepare_color(analyzed_element, [int(x * 255) for x in background_colors[0]])
        if color == color_before and background_colors == background_color_before:
            return None, None
        return color, background_colors

    @staticmethod
    def rgba_to_rgb(rgba, background=(255, 255, 255)):
        """
        convert rgba color to rgb
        :param rgba: [float, float, float, float]
        :param background: [int, int, int]
        :return: [float, float, float] - rgb format
        """
        r, g, b, a = rgba
        return [r * a + (1 - a) * background[0], g * a + (1 - a) * background[1], b * a + (1 - a) * background[2]]

    def get_rgb_color(self, color: str):
        return self.rgba_to_rgb(list(map(float, re.findall(r"\d*\.\d+|\d+", color)))) if color.startswith('rgba(') \
            else re.findall(r"\d+", Color.from_string(color).rgb)

    def prepare_background_color(self, analyzed_element: ElementWrapper):
        """
        FIXME
        :param analyzed_element:
        :return:
        """
        background_color = self.background(analyzed_element.framework_element)
        return [list(map(lambda x: float(x) / 255, self.get_rgb_color(color))) for color in background_color] if \
            background_color else [[1, 1, 1]]

    def get_opacity(self, analyzed_element: ElementWrapper):
        opacity = self.get_css(analyzed_element, "opacity")
        if opacity == '1':
            opacity = analyzed_element.element.find_element_by_xpath("parent::*").value_of_css_property("opacity")
        return opacity if opacity != '1' else None

    def prepare_color(self, analyzed_element: ElementWrapper, background_color: List[int]):
        """
        search color(color or background color)
        :param background_color:
        :param analyzed_element: (ElementWrapper)
        :return: list: The List of rgb species prepared for contrast test.
        """
        color = self.get_css(analyzed_element, "color")
        opacity = self.get_opacity(analyzed_element)
        if opacity is not None and color.startswith("rgb("):
            rgb = self.rgba_to_rgb(list(map(float, re.findall(r"\d*\.\d+|\d+", color))) + [float(opacity)],
                                   background_color)
        else:
            rgb = self.rgba_to_rgb(list(map(float, re.findall(r"\d*\.\d+|\d+", color))), background_color) \
                if color.startswith('rgba(') else re.findall(r"\d+", Color.from_string(color).rgb)
        return list(map(lambda x: int(x) / 255, rgb))

    def background(self, element: ElementWrapper, gradient: List[int] = None, pseudo_background: str = ""):
        """
        Looks for the background color of an element, gradually moving to the parent until it finds a color

        Warning:
            If the site DOM is too nested (more than 1000 elements), a recursion error will occur.

        Parameters:
            element (ElementWrapper)
            gradient
            pseudo_background
        Returns:
            Str:  background-color
        """
        if element is None:
            return [pseudo_background] if pseudo_background else gradient
        if gradient is None:
            gradient = []

        wrap = self._wrap(element)
        background_color = wrap.css_property('background-color')
        if not background_color or background_color == 'rgba(0, 0, 0, 0)':
            for pseudo in ['after', 'before']:
                background = self.get_pseudo_element_attribute(pseudo, wrap.element, "background-color")
                opacity = self.get_pseudo_element_attribute(pseudo, wrap.element, "opacity")
                if not pseudo_background and background.startswith("rgb(") and opacity != "0":
                    pseudo_background = background
            background_image = wrap.css_property('background-image')
            if background_image != 'none' and background_image.startswith('linear-gradient') and not gradient:
                gradient = re.findall(r"rgb\(.*?\)", background_image) or re.findall(r"rgba\(.*?\)", background_image)
            return self.background(wrap.framework_element.get_parent(self._dr), gradient, pseudo_background)
        return [background_color]

    @staticmethod
    def get_css(wrap_element: ElementWrapper, css_property: str):
        return wrap_element.css_property(css_property)
