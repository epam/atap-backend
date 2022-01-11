import re
import unicodedata
from typing import List
from math import inf

from selenium import webdriver
from selenium.webdriver.support.color import Color

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.libs.element_rect import WebElementRect
from framework.libs.distance_between_elements import contains
from framework.tests.contrast.check_contrast import contrast
from framework.libs.is_visible import is_visible

name = '''Ensures that contrast ratio for text and non-text elements does not violate requirements (1.4.3, 1.4.11)'''
WCAG = '1.4.3'
framework_version = 5
webdriver_restart_required = False

elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "contrast/page_good_lite_contrast.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "contrast/page_bugs_lite_contrast.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    }
]


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """
    :param webdriver_instance (webdriver.Firefox):
    :param activity (Activity):
    :param element_locator (ElementLocator):
    :return: result dict
            {
                'status': <'FAIL', 'PASS' or 'NOELEMENTS'>,
                'message': <string>,
                'elements': [
                    {
                        "element": <Element>,
                        "problem": ...,
                        "severity": "WARN"/"FAIL",
                        "error_id": "TextContrast"/"ObjectContrast"

                    }],
                'checked_elements': [<Element>, ...]
             }
    """
    activity.get(webdriver_instance)
    return LiteContrast(webdriver_instance, element_locator).result()


class LiteContrast:

    def __init__(self, driver: webdriver.Firefox, locator: ElementLocator):
        self._dr = driver
        self._loc = locator
        self._coords = None

    def _wrap(self, el: Element) -> ElementWrapper:
        return ElementWrapper(el, self._dr)

    def result(self) -> dict:
        """
        :return: result dict
        """
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

    def get_param(self, wrap: ElementWrapper, text: str, size: float, bold: bool) -> float:
        """
        Checks for conditions for contrast.
        Parameters:
            wrap (ElementWrapper)
            text (str): visible text of web element
            size (float): font size, px
            bold (bool): font weight (True if text is bold)
        Returns:
            float: coefficient for checking contrast.
        """
        # because size - px, not point
        if self.detect_graphic_object(wrap, text) or (size >= 18.66 and bold) or (size >= 24 and not bold):
            return 3
        else:
            return 4.5

    def get_text(self, element: ElementWrapper):
        """
        :param element: (ElementWrapper)
        :return: text (str), "" or "placeholder" (if element <input> and have 'placeholder' attribute)
        """
        text = element.text.strip()
        if not text:
            attributes = element.framework_element.get_attributes(self._dr)
            if 'placeholder' in attributes:
                return attributes['placeholder'], 'placeholder'
        return text, ""

    @staticmethod
    def filter_before_checking(element: ElementWrapper):
        """
        Checks whether this element should be checked. The element is not checked if 'display' = 'block' and
        'text-indent' (this means that the element will not be visible on the page). Elements whose child text elements
         are fully included in the check are also skipped.
        :param element: (ElementWrapper)
        :return: (bool) 'true' if we leave the item for verification else 'false'
        """
        if element.css_property('display') == 'block' and element.css_property('text-indent') == '-9999px':
            return False
        text = element.text.strip()
        children_with_text = list(filter(lambda x: x.text.strip(), element.element.find_elements_by_xpath('child::*')))
        if children_with_text:
            for child in children_with_text:
                text = text.replace(child.text.strip(), '', 1)
            return text.strip()
        return True

    def detect_graphic_object(self, wrap: ElementWrapper, text: str):
        return (text and all([unicodedata.category(i) == 'So' for i in text])) or not self.text_is_visible(wrap)

    @staticmethod
    def text_is_visible(wrap: ElementWrapper):
        return wrap.css_property('font-size') != "0px" \
               and (wrap.css_property("overflow") != "hidden"
                    or (wrap.element.size["height"] > 5 and wrap.element.size["width"] > 5))

    def search_bad_text(self):
        """
        This method searches the page for all elements with text.
        After that, he takes the background-color and color from each element,
        and checks the contrast using the formula.

        Returns: the list with elements with bad contrast.
        """
        bad_elements = {}
        bad_elements_with_gradient = []
        checked_elements = []
        group_elements = ['self::title', 'self::style', 'self::script', 'self::noscript']
        xpath = f"//body//*[self::span or self::*[(@placeholder or text()) and not({' or '.join(group_elements)})]]"
        text_elements = sorted(
            self._loc.get_all_by_xpath(self._dr, xpath),
            key=lambda x: (-x.safe_operation_wrapper(lambda i: i.get_element(self._dr).location['y'], on_lost=lambda: inf),
                           -x.safe_operation_wrapper(lambda i: i.get_element(self._dr).location['x'], on_lost=lambda: inf))
        )

        def check_contrast(element: Element):
            analyzed_element = self._wrap(element)
            if not self.filter_before_checking(analyzed_element) or not analyzed_element.is_visible:
                return None
            text, pseudo = self.get_text(analyzed_element)
            if not text:
                return None
            checked_elements.append(analyzed_element.framework_element)
            bold = int(self.get_css(analyzed_element, "font-weight")) >= 700
            size = float(re.search(r"\d+", self.get_css(analyzed_element, 'font-size'))[0])
            color_1, color_2, animation = self.contrast(analyzed_element, pseudo)
            key = (tuple(color_1), tuple(color_2), animation.get("image", None))
            if key in bad_elements and "gradient" not in animation:
                return None
            text_contrast, severity = self.check_contrast(color_1, color_2, self.get_param(analyzed_element, text, size, bold), animation)
            if not text_contrast and "gradient" not in animation:
                bad_elements[key] = self.bad_element(analyzed_element, pseudo, severity, text)
            elif not text_contrast:
                bad_elements_with_gradient.append(self.bad_element(analyzed_element, pseudo, severity, text))
        Element.safe_foreach(text_elements, check_contrast)
        return checked_elements, self.filter(bad_elements_with_gradient + list(bad_elements.values()))

    def bad_element(self, analyzed_element, pseudo, severity, text):
        return {
            "element": analyzed_element.framework_element,
            "problem": f"Bad contrast",
            "severity": "WARN" if pseudo else severity,
            "error_id": "ObjectContrast" if self.detect_graphic_object(analyzed_element, text) else "TextContrast"
        }

    def filter(self, elements: List[dict]) -> List[dict]:
        """
        Filters elements: removes duplicates of elements (if there is a parent element and its descendants in the list,
         only the descendants will remain in the list).
        :param elements:
        [{"element": <Element>, "problem": ..., "severity": "WARN"/"FAIL", "error_id": "TextContrast"/"ObjectContrast"}]
        :return: list of dicts
        """
        descendants = list(map(
            lambda x: x.source, sum([e["element"].find_by_xpath('descendant::*', self._dr) for e in elements], [])))
        return list(filter(lambda x: x["element"].source not in descendants, elements))

    @staticmethod
    def rgba_to_rgb(rgba: List[float], background=(255, 255, 255)):
        """
        convert rgba color to rgb
        :param rgba: [float, float, float, float]
        :param background: [int, int, int]
        :return: [float, float, float], rgb format
        """
        r, g, b, a = rgba
        return [r * a + (1 - a) * background[0], g * a + (1 - a) * background[1], b * a + (1 - a) * background[2]]

    def check_contrast(self, color_1, color_2, param, animation):
        return contrast(color_1, color_2) >= param and "image" not in animation, "WARN" if animation else "FAIL"

    def contrast(self, analyzed_element: ElementWrapper, pseudo: str):
        """
        Check contrast by formula using relative luminance

        Parameters:
            analyzed_element (ElementWrapper)
            param (int)
            pseudo (bool)
        Returns:
            float: contrast
            str: severity
        """
        # color background
        color_2, animation = self.prepare_color(analyzed_element, "background-color", pseudo, [])
        # color of element (or pseudo element if this element has placeholder)
        color_1, _ = self.prepare_color(analyzed_element, "color", pseudo, list(map(lambda x: x * 255, color_2)))
        return color_1, color_2, animation

    def prepare_background_color(self, analyzed_element: ElementWrapper):
        """
        find background color
        :param analyzed_element: (ElementWrapper)
        :return: [float, float, float], bool
        """
        rgb = [255, 255, 255]
        background = self.background(analyzed_element.framework_element)
        css_property = self.search_css_property(analyzed_element)
        animation_background = {}
        if "animation" in css_property:
            animation_background = {"image": css_property["animation"]}
        elif "image" in background:
            animation_background = {"image": background["image"]}
        if ('background-color' in background
                and ('element' not in css_property or self.compare_sizes(background['element'], css_property['element']))):
            rgb = background['background-color']
            if 'animation' in css_property and self.compare_sizes(background['element'], css_property['animation']):
                animation_background = {}
        elif 'fill' in css_property:
            rgb = css_property['fill']
        elif ('gradient' in background
              and ('element' not in css_property or self.compare_sizes(background['gradient_element'], css_property['element']))):
            color = min(background['gradient'])
            rgb = self.rgba_to_rgb(list(map(float, re.findall(r"\d*\.\d+|\d+", color)))) \
                if color.startswith('rgba(') else self.get_rgb(color)
            if not animation_background:
                animation_background = {"gradient": ""}
        elif 'background-color' in css_property:
            rgb = css_property['background-color']
            if "animation" in css_property:
                animation_background = {"image": css_property["animation"]}
            else:
                animation_background = {}
        elif 'pseudo_background' in background:
            rgb = self.get_rgb(background['pseudo_background'])
        elif 'background-color' in background:
            rgb = self.get_rgb(background['background-color'])
        return list(map(lambda x: x / 255, rgb)), animation_background

    def prepare_color(self, analyzed_element: ElementWrapper, prop: str, pseudo: str, background_color: List[int]):
        """ search color(color or background color)
        Parameters:
            analyzed_element (ElementWrapper)
            prop (str): property for value from css ("background-color" or "color")
            pseudo (bool) if true: this is element with placeholder(search color of pseudo element)
            background_color (List[int])
        Returns:
            list: The List of rgb species prepared for contrast test.
        """
        if prop == "background-color":
            return self.prepare_background_color(analyzed_element)
        elif not pseudo:
            color = self.get_css(analyzed_element, prop)
        else:
            def script(w): return f"return window.getComputedStyle(arguments[0],'::{pseudo}').getPropertyValue('{w}')"
            color = self._dr.execute_script(
                script('color'),
                analyzed_element.element
            )
            opacity = self._dr.execute_script(
                script('opacity'),
                analyzed_element.element
            )
            if opacity and color.startswith('rgb('):
                rgb = self.rgba_to_rgb(list(map(float, re.findall(r"\d*\.\d+|\d+", color))) + [float(opacity)],
                                       background_color)
                return list(map(lambda x: x / 255, rgb)), False
        rgb = self.rgba_to_rgb(list(map(float, re.findall(r"\d*\.\d+|\d+", color))), background_color) \
            if color.startswith('rgba(') else self.get_rgb(color)
        return list(map(lambda x: x / 255, rgb)), False

    @staticmethod
    def get_rgb(color: str):
        """
        Converts any color format to rgb and extracts from string

        Parameters:
            color (str)
        Returns:
            list: Ready list with rgb color of element.
        """
        return list(map(int, re.findall(r"\d+", Color.from_string(color).rgb)))

    def pseudo_element_background_color(self, wrap: ElementWrapper, result: dict):
        """
        FIXME
        :param result:
        :param wrap:
        :return:
        """
        for pseudo in ['after', 'before']:
            background_color = self._dr.execute_script(
                f"return window.getComputedStyle(arguments[0],':{pseudo}').getPropertyValue('background-color')",
                wrap.element
            )
            if background_color and background_color.startswith('rgb('):
                result.update({'pseudo_background': background_color})
                return True
        return False

    def background(self, element: Element, result=None):
        """
        Looks for the background color of an element, gradually moving to the parent until it finds a color

        Warning:
            If the site DOM is too nested (more than 1000 elements), a recursion error will occur.

        Parameters:
            :param element:
            :param result:
        """
        if result is None:
            result = dict()
        if element is None:
            return result
        wrap = self._wrap(element)
        background_color = wrap.css_property('background-color')
        if not background_color or not background_color.startswith('rgb('):
            if 'pseudo_background' not in result and not self.pseudo_element_background_color(wrap, result):
                background_image = wrap.css_property('background-image')
                if background_image != 'none' and background_image.startswith('linear-gradient'):
                    result.update({'gradient': (re.findall(r"rgb\(.*?\)", background_image)
                                                or re.findall(r"rgba\(.*?\)", background_image)),
                                   'gradient_element': wrap.element})
                    return result
                elif background_image != 'none' and background_image.startswith('url(') and wrap.element.tag_name not in ['body', 'html']:
                    result.update({'image': wrap.element})
                    return result
            return self.background(wrap.framework_element.get_parent(self._dr), result)
        result.update({'background-color': self.get_rgb(background_color), 'element': wrap.element})
        return result

    def compare_size_with_window(self, elem) -> bool:
        window_size = self._dr.get_window_size()
        return elem.size['height'] < window_size['height'] - 75 or elem.size['width'] < window_size['width'] - 75

    @staticmethod
    def compare_sizes(elem1, elem2):
        return elem1.size['height'] * elem1.size['width'] < elem2.size['height'] * elem2.size['width']

    def search_css_property(self, analyzed_element: ElementWrapper):
        """
        Since sometimes websites use canvas and elements may not have a background color,
        this method is used to find that color through the fill attribute.

        Parameters:
            analyzed_element (ElementWrapper)

        Returns:
            list or None: Ready list with rgb color of element or None if no elements what have fill attribute.
        """
        elements = WebElementRect(analyzed_element.element).plural_intersects(self.coords())
        result = dict()
        for el in elements:
            if ('animation' not in result and el.tag_name in ['video', 'img'] and is_visible(el, self._dr)
                    and self.compare_sizes(analyzed_element.element, el)
                    and contains(self._dr, el, analyzed_element.element)):
                result.update({'animation': el})
            fill = el.value_of_css_property('fill')
            if fill != 'none' and self.get_rgb(fill) != [0, 0, 0]:
                return {'fill': self.get_rgb(fill)}
            if (is_visible(el, self._dr) and self.compare_sizes(analyzed_element.element, el)
                    and ('background-color' not in result or contains(self._dr, result['element'], el))
                    and self.compare_size_with_window(el) and contains(self._dr, el, analyzed_element.element)):
                background_color = el.value_of_css_property('background-color')
                if background_color.startswith('rgb('):
                    result.update({'background-color': self.get_rgb(background_color), 'element': el})
        if 'animation' in result and 'background-color' in result and self.compare_sizes(
                result['element'], result['animation']):
            result.pop('animation')
        return result

    def coords(self):
        """
        Returns: dict: The Dict with element and his coordinates.
        """
        if self._coords is not None:
            return self._coords
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
        self._coords = dict_coords
        return dict_coords

    @staticmethod
    def get_css(analyzed_element: ElementWrapper, css_property: str):
        """
        Parameters:
            analyzed_element (ElementWrapper):
            css_property (str): value of css property
        Returns:
            str: The List of rgb species prepared for contrast test.
        """
        return analyzed_element.css_property(css_property)

    def visible_elements(self, elements: List[Element]):
        """
        Parameters:
            elements (list): list with framework elements
        Returns:
            list: The List of with only visible elements.
        """
        return [el for el in elements if self._wrap(el).is_visible]
