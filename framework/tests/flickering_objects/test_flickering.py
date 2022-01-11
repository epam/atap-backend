import base64
import itertools
import tempfile
from time import sleep

import cv2
import imutils
from PIL import Image
from selenium import webdriver
import numpy as np
from selenium.webdriver.remote.webelement import WebElement
from skimage.measure import compare_ssim

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.element_rect import WebElementRect
from framework.tests.flickering_objects.base_func import black2white, calculation

name = "Ensures that page don't have flickering elements"
WCAG = "2.2.2"
framework_version = 4
depends = []
webdriver_restart_required = False
elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "flicker/page_good_flickering.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "flicker/page_bad_flickering.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]
_OTHER_TAGS = {
    'br',
    'script',
    'body'
}


def check_images(dr: webdriver.Chrome, previous, height, images_path: tuple = None):
    def all_coordinates() -> dict:
        """
        TODO: It is necessary to update the Element, adding functionality ElementRect
        :return: dict with all elements with there coordinates on page
        """
        elements = dr.find_elements_by_xpath('//body/*')
        elements = [e for e in elements if e.tag_name != "script"]
        return {e: WebElementRect(e) for e in elements if e.size['width'] * e.size['height'] > 0}

    print("Began searching for a flickering element")
    changed_items = []
    changed = set()
    if previous is None:
        height = 0

    (score, diff) = compare_ssim(
        cv2.cvtColor(np.array(Image.open(images_path[0]).convert("RGB")), cv2.COLOR_RGBA2GRAY),
        cv2.cvtColor(np.array(Image.open(images_path[1]).convert("RGB")), cv2.COLOR_RGBA2GRAY),
        full=True)

    diff = (diff * 255).astype("uint8")

    threshold = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    cnts = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    for c in cnts:
        (x, y, w, h) = cv2.boundingRect(c)
        changed_items.append(WebElementRect.from_rect(x, y + height, w, h))

    for rect in changed_items:
        for el, coordinates in all_coordinates().items():
            if rect.intersects(coordinates) and el.tag_name not in _OTHER_TAGS and is_visible(el):
                changed.add(el)

    return [el for el in Element.from_webelement_list(changed, dr)
            if not (el.tag_name == "img" and el.get_attribute(dr, "src").endswith(".gif"))]


def is_visible(element: WebElement):
    return element.size['width'] * element.size['height'] > 0


def prepare_screens(screens_as_base64):
    return [base64.b64decode(screen.encode('ascii')) for screen in screens_as_base64]


def get_list_images(dr, path):
    path_images = []
    time_sleep = 0
    screens = []
    for i in range(1, 33):
        if i % 8 == 0:
            time_sleep += 0.03
        sleep(time_sleep)
        screens.append(dr.get_screenshot_as_base64())
    screens = [base64.b64decode(screen.encode('ascii')) for screen in screens]
    for img in enumerate(screens):
        filename = f'{path}/image_{img[0]}.png'
        path_images.append(filename)
        with open(filename, 'wb') as f:
            f.write(img[1])
    return path_images


def flickers(dr, path):
    result = [black2white(path) for path in get_list_images(dr, path)]
    for img1, img2 in itertools.combinations(result, 2):
        if calculation(img1[0], img2[0], 20.0) and calculation(img1[1], img2[1], 20.0):
            return img1[2], img2[2]
    return True


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator):
    """..."""
    activity.get(webdriver_instance)
    path_folder = tempfile.TemporaryDirectory("images_", "_flicker")
    webdriver_instance.execute_script(f"window.scrollTo({0}, {0})")
    total_width = webdriver_instance.execute_script("return document.body.offsetWidth")
    total_height = webdriver_instance.execute_script("return document.body.parentNode.scrollHeight")
    viewport_width = webdriver_instance.execute_script("return document.body.clientWidth")
    viewport_height = webdriver_instance.execute_script("return window.innerHeight")
    rectangles = []
    SCROLL_COUNT = 0
    i = 0
    while i < total_height:
        ii = 0
        top_height = i + viewport_height
        if top_height > total_height:
            top_height = total_height
        while ii < total_width:
            top_width = ii + viewport_width
            if top_width > total_width:
                top_width = total_width
            rectangles.append((ii, i, top_width, top_height))
            ii = ii + viewport_width
        i = i + viewport_height
    previous = None
    for rectangle in rectangles:
        if SCROLL_COUNT > 4:
            break
        if previous is not None:
            webdriver_instance.execute_script(f"window.scrollTo({rectangle[0]}, {rectangle[1]})")
            SCROLL_COUNT += 1
        result = flickers(webdriver_instance, path_folder.name)
        if isinstance(result, tuple):
            imgs = check_images(webdriver_instance, previous, viewport_height, result)
            if not imgs:
                print("Defining an element by coordinates on this page failed")
                bad_elements = [dict(element=element_locator.get_all_by_xpath(webdriver_instance, "//body")[0],
                                     problem="One of the elements on the page is flickering",
                                     error_id="Flicker")]
            else:
                bad_elements = [dict(element=el, problem="Element flickers", error_id="Flicker")
                                for el in imgs]
            return dict(status="FAIL", message="This page have flickering objects", elements=bad_elements,
                        checked_elements=[])
        previous = rectangle
    return dict(status="PASS", message="This page don't have flickering objects", checked_elements=[])
