import random
from time import sleep

import imutils
from selenium import webdriver

import cv2 as cv
from skimage.measure import compare_ssim

from framework.element import Element
from framework.libs.element_rect import WebElementRect
from framework.screenshot.screenshot import Screenshot
from framework.tests.countdowns.interface import Test
import numpy as np

_OTHER_TAGS = {  # Tags for elements what by mistake, may be taken in attention
    'br',
    'script',
}


class TestByOpenCv(Test):
    @staticmethod
    def changed(webdriver_instance: webdriver.Chrome, element_locator) -> []:
        """
        This method check changes by 2 screen shots,
        with a sleep between them.
        After if page have changes returned list with updated items.


        :param element_locator:
        :param webdriver_instance: webdriver of browser
        :return: list with list pf problems elements, or empty list
        """

        def all_coordinates():
            """
            TODO: It is necessary to update the Element, adding functionality ElementRect
            :return: dict with all elements with there coordinates on page
            """
            elements = webdriver_instance.find_elements_by_xpath('//body//*[not(*)]')
            return {e: WebElementRect(e) for e in elements if e.size['width'] * e.size['height'] > 0}

        def grayscale_image():

            im = Screenshot.full_page(webdriver_instance)
            return cv.cvtColor(np.array(im), cv.COLOR_RGB2GRAY)

        print("====>Start testing by screenshots")
        changed_items = []  # List with changed element founded by opencv
        changed = set()  # Set with changed elements, without normal registration
        bad_elements = []

        gray_a = grayscale_image()
        sleep(10)
        gray_b = grayscale_image()

        (score, diff) = compare_ssim(gray_a, gray_b, full=True)
        diff = (diff * 255).astype("uint8")

        threshold = cv.threshold(diff, 0, 255, cv.THRESH_BINARY_INV | cv.THRESH_OTSU)[1]
        cnts = cv.findContours(threshold.copy(), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        for c in cnts:
            (x, y, w, h) = cv.boundingRect(c)
            changed_items.append(WebElementRect.from_rect(x, y, w, h))

        for rect in changed_items:
            for el, coordinates in all_coordinates().items():
                if rect.intersects(coordinates) and el.tag_name not in _OTHER_TAGS:
                    changed.add(el)

        if len(changed) > 0:
            for el in changed:
                bad_elements.append({
                    "element": Element(el, webdriver_instance),
                    "problem": "Not decorated"
                })
        return bad_elements
