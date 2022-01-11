import imutils
from selenium import webdriver
import cv2 as cv
from selenium.common.exceptions import ElementNotInteractableException
import numpy as np
from skimage.measure import compare_ssim
from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.element_rect import WebElementRect
from framework.screenshot.screenshot import Screenshot

name = "Ensures that tooltips close after unfocus"
WCAG = "1.4.13"
framework_version = 0
webdriver_restart_required = False

elements_type = "tooltip"
test_data = [
    {
        "page_info": {
            "url": "tooltips/page_good_tooltips.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tooltips/page_bugs_tooltips.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator):
    """
    :param webdriver_instance:
    :param activity:
    :param element_locator:
    :return:
    """
    activity.get(webdriver_instance)

    return Tooltips(webdriver_instance, activity, element_locator).result()


class Previous(object):
    """Class for storing the previous element and information about it"""
    def __init__(self, element, screenshot, changes):
        if not isinstance(element, Element):
            raise TypeError("Incorrect type object")
        self._el = element
        self._scr = screenshot
        self._ch = changes

    @property
    def el(self):
        return self._el

    @property
    def scr(self):
        return self._scr

    @property
    def ch(self):
        return self._ch


class Tooltips:
    def __init__(self, driver: webdriver.Firefox, activity: Activity, locator):
        self._dr = driver
        self._ac = activity
        self._loc = locator

    def result(self):
        """Formation of the final dict"""
        result = {
            "status": "PASS",
            "message": "Found tooltips, what work correctly",
            "elements": [],
            "checked_elements": [],
        }
        elements = self.main()
        if elements is None:
            result["status"] = "NOELEMENTS"
            result["message"] = "This page no problem with tooltips"
        elif elements:
            result["status"] = "FAIL"
            result["elements"] = elements
            result["message"] = "Found incorrectly worked tooltips"
        return result

    def local_src(self, el: Element):
        """Small wrapper for screenshot"""
        i = Screenshot(self._dr, el).single_element(safe_area=200)
        i.save(f"{el.tag_name}_{el.source[:10]}.png")
        return Screenshot(self._dr, el).single_element(safe_area=200)

    def interactable_elements(self):
        """Search only interactable elements"""
        return [el for el in self._loc.get_all_by_xpath(self._dr, "//body//*") if self.__is_visible(el)]

    def main(self):
        """Main func of test"""
        bad_tooltips = []
        elements = self.interactable_elements()
        if not elements:
            return None
        self._ac.get(self._dr)

        prev = None

        for element in elements:

            zero_screen = self.local_src(element)

            element.get_element(self._dr).send_keys('')

            if prev is not None \
                    and self.check_changes(prev.ch, self.get_changes(prev.scr, self.local_src(prev.el))):
                bad_tooltips.append({
                    "element": prev.el,
                    "problem": "Tooltip did't disappear after unfocus.",
                    "severity": "FAIL"
                })

            second_screen = self.local_src(element)
            changes = self.get_changes(zero_screen, second_screen)

            web_element = element.get_element(self._dr)

            for coordinates in changes:
                distance = WebElementRect(web_element).get_distance(coordinates)
                if 5 < min(distance) < 100:
                    prev = Previous(element, second_screen, changes)
        return bad_tooltips

    def get_changes(self, image_1, image_2):
        """Method for finding changes between 2 images"""
        changed_items = []
        gray_1 = self.grayscale_image(image_1)
        gray_2 = self.grayscale_image(image_2)

        (score, diff) = compare_ssim(gray_1, gray_2, full=True)
        diff = (diff * 255).astype("uint8")
        threshold = cv.threshold(diff, 0, 255,
                                 cv.THRESH_BINARY_INV | cv.THRESH_OTSU)[1]
        contours = cv.findContours(threshold.copy(), cv.RETR_EXTERNAL,
                                   cv.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(contours)

        for contour in contours:
            (x, y, w, h) = cv.boundingRect(contour)
            changed_items.append(WebElementRect.from_rect(x, y, w, h))
        return changed_items

    def __is_visible(self, element: Element):
        """Check if an element is visible"""
        el = element.get_element(self._dr)
        if not el.is_displayed():
            # In order not to do unnecessary actions
            return False
        try:
            el.send_keys('')
        except ElementNotInteractableException:
            return False
        return True

    @staticmethod
    def grayscale_image(image):
        """Convert image"""
        return cv.cvtColor(np.array(image), cv.COLOR_RGB2GRAY)

    @staticmethod
    def check_changes(prev_changes, new_changes):
        return any([ch for ch in prev_changes if ch in new_changes])