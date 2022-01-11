import re
import time
import tempfile
from typing import List

from selenium import webdriver
from selenium.webdriver.support.color import Color
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.libs.element_rect import WebElementRect
from framework.tests.contrast import check_contrast
from framework.screenshot.screenshot import Screenshot


name = "Ensures that border is in contrast in focus"
WCAG = '1.4.11'
framework_version = 5
webdriver_restart_required = False
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "contrast/page_good_border.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "contrast/page_bug_border.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]

DELAY_AFTER_ACTION = 1.5
MAXIMUM_DEPTH_OF_VERIFICATION = 40000


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """

    """
    activity.get(webdriver_instance)
    return BorderContrast(webdriver_instance, element_locator).result()


class BorderContrast:

    def __init__(self, driver, locator: ElementLocator):
        self._dr = driver
        self._loc = locator
        self._coords = None

    def _wrap(self, el):
        return ElementWrapper(el, self._dr) if el is not None else None

    def result(self):
        result = {
            "status": "NOELEMENTS",
            "message": "",
            "elements": [],
            "checked_elements": [],
            "labels": []
        }
        checked_elements, bad_elements = self.search_bad_text()
        if not bad_elements and checked_elements:
            result["status"] = "PASS"
            result["message"] = "This page no problem with contrast"
            result["checked_elements"] = checked_elements
        elif checked_elements:
            result["status"] = "FAIL"
            result["elements"] = bad_elements
            result["message"] = "Page has problems with contrast"
            result["checked_elements"] = checked_elements
        print(result)
        return result

    def add_screenshot(self, element: Element, result: dict):
        screen = Screenshot(self._dr, element).single_element(safe_area=100)
        if screen:
            file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            screen.save(file.name)
            result["screenshot"] = file.name

    def get_next_element(self, current_element, checked_elements):
        next_element = self.focus_on_next(current_element)
        # Fake focus
        if next_element is not None and next_element.element.tag_name in ("body", "html"):
            next_element = self.focus_on_next(current_element)
        if (next_element is None or next_element.element.tag_name in ("body", "html")
                or next_element in checked_elements or list(next_element.location)[1] > MAXIMUM_DEPTH_OF_VERIFICATION):
            return None
        return next_element

    def focus_on_next(self, element: ElementWrapper):
        try:
            element.send_keys(Keys.TAB)
            time.sleep(DELAY_AFTER_ACTION)
            return self._wrap(Element(self._dr.switch_to.active_element, self._dr))
        except WebDriverException:
            return None

    def create_border_absent_bug(self, elements_with_not_visible_border: List[dict], element: Element):
        element_dict = {
            "element": element,
            "problem": "Border is not visible",
            "error_id": "BorderAbsent",
            "severity": 'FAIL'
        }
        self.add_screenshot(element, element_dict)
        elements_with_not_visible_border.append(element_dict)

    def search_bad_text(self):
        """
        This method searches the page for all elements with text.
        After that, he takes the background-color and color from each element,
        and checks the contrast using the formula.

        Returns:
            bool:The List with elements with bad contrast.
        """
        bad_elements = dict()
        elements_with_not_visible_border = []
        body = self._dr.find_elements_by_xpath("//body")[0]
        element_borders = {e: (list(map(lambda x: x / 255, self.get_rgb_color(self.get_css(self._wrap(e), "border-top-color"))))
                               if self.get_css(self._wrap(e), "border-top-style") != 'none' else None)
                           for e in body.find_elements_by_xpath("descendant::*")}

        try:
            body.send_keys(Keys.TAB)
            time.sleep(DELAY_AFTER_ACTION)
        except WebDriverException:
            return [], []

        active_element = self._dr.switch_to.active_element
        if active_element == body:
            return [], []

        checked_elements = []
        analyzed_element = self._wrap(Element(active_element, self._dr))
        while analyzed_element is not None:
            # logo
            if (analyzed_element.element.tag_name in ['img', 'svg', 'i']
                    and (analyzed_element.framework_element.source.find('logo') != -1
                         or analyzed_element.framework_element.find_by_xpath('parent::*', self._dr)[0].source.find('logo') != -1)):
                analyzed_element = self.get_next_element(analyzed_element, checked_elements)
                continue

            if analyzed_element.element.tag_name in ['input', 'textarea']:
                analyzed_element = self.get_next_element(analyzed_element, checked_elements)
                continue
            checked_elements.append(analyzed_element.framework_element)
            border_is_visible = self.get_css(analyzed_element, "box-shadow") != "none" or self.get_css(analyzed_element, "outline-style") != "none"
            if analyzed_element.is_visible and not border_is_visible:
                self.create_border_absent_bug(elements_with_not_visible_border, analyzed_element.framework_element)
            elif analyzed_element.is_visible:
                border, background, contrast, background_info = self.contrast(analyzed_element)
                border_before = element_borders[analyzed_element.element]
                if border_before is not None and border_before == border:
                    self.create_border_absent_bug(elements_with_not_visible_border, analyzed_element.framework_element)
                else:
                    key = (tuple(background), tuple(border))
                    if (background_info != 'empty' and (contrast < 3 or background_info == 'animation')
                            and key not in bad_elements):
                        bad_elements[key] = {
                            "element": analyzed_element.framework_element,
                            "problem": "Bad contrast (border)",
                            "severity": "WARN" if background_info == 'animation' else 'FAIL',
                            "error_id": "BorderContrast"
                        }
                        self.add_screenshot(analyzed_element.framework_element, bad_elements[key])
            analyzed_element = self.get_next_element(analyzed_element, checked_elements)
        return checked_elements, elements_with_not_visible_border + list(bad_elements.values())

    def get_pseudo_element_attribute(self, pseudo: str, element: WebElement, attr: str = 'content') -> str:
        return self._dr.execute_script(
            f"return window.getComputedStyle(arguments[0], ':{pseudo}').getPropertyValue('{attr}');", element)

    def get_border_color(self, wrap_element: ElementWrapper, background_color: List[int] = None):
        if background_color is None:
            background_color, _ = self.prepare_color(wrap_element, "background-color")
        border_color, _ = self.prepare_color(wrap_element, "outline-color", background_color)
        return border_color

    def contrast(self, wrap_element: ElementWrapper):
        """
        Check contrast by formula using relative luminance

        Parameters:
            wrap_element (ElementWrapper)
        Returns:
            float: contrast
            str: severity
        """
        # color background
        background_color, background_info = self.prepare_color(wrap_element, "background-color")
        # focus border color
        border_color, _ = self.prepare_color(wrap_element, "outline-color", background_color)
        if wrap_element.element.tag_name in ['button']:
            button_color = [i / 255 for i in self.get_rgb_color(self.get_css(wrap_element, 'background-color'))]
            if check_contrast.contrast(border_color, button_color) < check_contrast.contrast(border_color, background_color):
                return border_color, button_color, check_contrast.contrast(border_color, button_color), None
        return border_color, background_color, check_contrast.contrast(border_color, background_color), background_info

    def prepare_color(self, wrap_element: ElementWrapper, prop: str, background_color: List[int] = None):
        """

        Parameters:
            wrap_element (ElementWrapper)
            prop (str): property for value from css
            background_color (List[int])
        Returns:
            list: The List of rgb species prepared for contrast test.
        """
        background_info = ""
        if prop == "background-color":
            fill, background_color, animation_background = self.search_css_property(wrap_element)
            if fill is not None:
                rgb = fill
            else:
                background, animation = self.background(
                    wrap_element if wrap_element.element.tag_name != 'button'
                    else self._wrap(wrap_element.framework_element.get_parent(self._dr))
                )
                rgb = self.get_rgb_color(background) if background is not None \
                    else (background_color if background_color is not None else [255, 255, 255])
                if animation_background is not None or animation:
                    background_info = "animation"
                elif background is None and background_color is None:
                    background_info = "empty"
        else:
            box_shadow = self.get_css(wrap_element, 'box-shadow')
            box_shadow = re.findall(r"rgb\(.*?\)", box_shadow) or re.findall(r"rgba\(.*?\)", box_shadow)
            rgb = self.get_rgb_color(box_shadow[0], background_color) if box_shadow \
                else self.get_rgb_color(self.get_css(wrap_element, prop), background_color)
        return list(map(lambda x: x / 255, rgb)), background_info

    @staticmethod
    def rgba_to_rgb(rgba, background):
        """
        convert rgba color to rgb
        :param rgba: [float, float, float, float]
        :param background: [int, int, int]
        :return: [float, float, float] - rgb format
        """
        r, g, b, a = rgba
        return [r * a + (1 - a) * background[0], g * a + (1 - a) * background[1], b * a + (1 - a) * background[2]]

    def get_rgb_color(self, color: str, background_color=(255, 255, 255)):
        return self.rgba_to_rgb(list(map(float, re.findall(r"\d*\.\d+|\d+", color))), background_color) \
            if color.startswith('rgba(') else [int(d) for d in re.findall(r"\d+", Color.from_string(color).rgb)]

    def background(self, wrap: ElementWrapper, animation=False):
        """
        Looks for the background color of an element, gradually moving to the parent until it finds a color

        Warning:
            If the site DOM is too nested (more than 1000 elements), a recursion error will occur.

        Parameters:
            wrap (ElementWrapper)
            animation (bool)

        Returns:
            Str:  background-color or None
        """
        if wrap is None:
            return None, animation

        background_color = wrap.css_property('background-color')
        background_image = wrap.css_property('background-image')
        if not animation and background_image != 'none':
            animation = True
        if not background_color or not background_color.startswith('rgb('):
            return self.background(self._wrap(wrap.framework_element.get_parent(self._dr)), animation)
        return background_color, animation

    def search_css_property(self, wrap_element):
        """
        Since sometimes websites use canvas and elements may not have a background color,
        this method is used to find that color through the fill attribute.

        Parameters:

        Returns:
            list or None: Ready list with rgb color of element or None if no elements what have fill attribute.
        """
        if self._coords is None:
            self._coords = self.coords()
        elements = WebElementRect(wrap_element.element).plural_intersects(self._coords)
        descendants = wrap_element.element.find_elements_by_xpath("descendant::*")

        background_color = None
        animation_background = None
        for el in elements:
            if el != wrap_element.element and animation_background is None and el.tag_name in ['video', 'img'] and \
                    el.size['height'] * el.size['width'] > 0 and el.is_displayed() and el not in descendants:
                animation_background = el

            fill = el.value_of_css_property('fill')
            if fill != 'none' and self.get_rgb_color(fill) != [0, 0, 0] and el not in descendants:
                return self.get_rgb_color(fill), None, None

            if background_color is None:
                background_color = self.get_rgb_color(el.value_of_css_property('background-color'))
                background_color = None if all([i == 0 for i in background_color]) else background_color

        return None, background_color, animation_background

    def coords(self):
        """
        Returns:
            dict: The Dict with element and his coordinates.
        """
        coords = self._dr.execute_script("""
              var elements_coords = [];
              var elements = Array.from(document.body.getElementsByTagName('*'));

              function get_coords(els){
                  els.forEach(function(el) {
                      var coord = el.getClientRects()[0];
                      if (coord != undefined && coord['width'] * coord['height'] > 0){
                          elements_coords.push({
                              'element': el,
                              'coords':  [coord['x'], coord['y'], coord['width'], coord['height']]
                          });
                      };
                  });
              };
              get_coords(elements);
              return elements_coords;
          """)
        dict_coords = {e['element']: e['coords'] for e in coords}
        return dict_coords

    def get_css(self, wrap_element, css_property):
        """
        Parameters:
            wrap_element (ElementWrapper)
            css_property (str): value of css property
        Returns:
            str: The List of rgb species prepared for contrast test.
        """
        return wrap_element.css_property(css_property)
