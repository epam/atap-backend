import tempfile
import time

import cv2
import numpy as np
import pytesseract
from PIL import Image
from selenium import webdriver

from framework.libs.download_image import get_image_element, wont_read_or_rgba
from framework.element_locator import ElementLocator, Element
from framework.tests.images.yolo import yolo_opencv


locator_required_elements = ["img"]
webdriver_restart_required = False
framework_version = 0
test_data = [
    {
        "page_info": {"url": "images/page_bug_image_with_text_m.html"},
        "expected_status": "PASS",
        "expected_additional_content_length": {"elements": 1},
    },
    {
        "page_info": {"url": "images/page_good_image_with_text.html"},
        "expected_status": "PASS",
        "expected_additional_content_length": {"elements": 1},
    },
]


BINARY_THREHOLD = 180
IMAGE_SIZE = 1800


class Rectangle:
    def __init__(self, x, y, h, w):
        self.h = h
        self.w = w
        self.dots = [(x, y), (x, y + h), (x + w, y + h), (x + w, y)]

    def check_dot_lies_in_rectangle(self, dot):
        return (
            dot[0] >= self.dots[0][0]
            and dot[1] >= self.dots[0][1]
            and dot[0] >= self.dots[1][0]
            and dot[1] <= self.dots[1][1]
            and dot[0] <= self.dots[2][0]
            and dot[1] <= self.dots[2][1]
            and dot[0] <= self.dots[3][0]
            and dot[1] >= self.dots[3][1]
        )

    def __gt__(self, other):
        for dot in other.dots:
            if not self.check_dot_lies_in_rectangle(dot):
                return False
        return True

    def __str__(self):
        return "Rectangle: {} {} {} {}".format(self.dots[0], self.dots[1], self.dots[2], self.dots[3])


def colors_histogram(image_name):
    img = cv2.imread(image_name)
    arr = np.asarray(img)
    flat = arr.reshape(int(np.prod(arr.shape[:2])), -1)
    try:
        a = np.sum(flat, 1) // flat.shape[1]
    except TypeError:
        return []
    bins = np.bincount(a.astype("int32"), minlength=256)
    return list(map(lambda x: x / sum(bins), bins))


def process_image_for_ocr(file_path):
    temp_filename = set_image_dpi(file_path).name
    remove_shadow(temp_filename)
    im_new = remove_noise_and_smooth(temp_filename)
    return im_new


def set_image_dpi(file_path):
    im = Image.open(file_path)
    length_x, width_y = im.size
    factor = max(1, int(IMAGE_SIZE / length_x))
    size = factor * length_x, factor * width_y
    im_resized = im.resize(size, Image.ANTIALIAS)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    temp_filename = temp_file.name
    im_resized.save(temp_filename, dpi=(300, 300))
    return temp_file


def image_smoothening(img):
    th1 = cv2.threshold(img, BINARY_THREHOLD, 255, cv2.THRESH_BINARY)[1]
    th2 = cv2.threshold(th1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    blur = cv2.GaussianBlur(th2, (1, 1), 0)
    th3 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return th3


def remove_noise_and_smooth(file_name):
    img = cv2.imread(file_name, 0)
    img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    filtered = cv2.adaptiveThreshold(
        img.astype(np.uint8), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 41, 3
    )
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(filtered, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
    img = image_smoothening(img)
    or_image = cv2.bitwise_or(img, closing)
    return or_image


def remove_shadow(file_path):
    img = cv2.imread(file_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.medianBlur(img, 5)
    rgb_planes = cv2.split(img)

    result_norm_planes = []
    for plane in rgb_planes:
        dilated_img = cv2.dilate(plane, np.ones((13, 13), np.uint8))
        bg_img = cv2.medianBlur(dilated_img, 17)
        diff_img = 255 - cv2.absdiff(plane, bg_img)
        norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        result_norm_planes.append(norm_img)

    result_norm = cv2.merge(result_norm_planes)
    cv2.imwrite(file_path, result_norm)


def get_text_from_image(image_name):
    image = process_image_for_ocr(image_name)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    filename = temp.name
    cv2.imwrite(filename, image)
    img = cv2.imread(filename)
    rectangles = []
    try:
        d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(img, config="-l eng + equ")
        n_boxes = len(d["level"])
        for i in range(n_boxes):
            if i == 0:
                continue
            (x, y, w, h) = (d["left"][i], d["top"][i], d["width"][i], d["height"][i])
            rectangles.append(Rectangle(x, y, h, w))
        temp.close()
        return text, rectangles, img.shape
    except pytesseract.pytesseract.TesseractNotFoundError:
        print("!!! Tesseract was not installed and/or added to PATH !!!")
        temp.close()
        return None, None, None


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):
    time1 = time.time()
    conclusion = {"status": "PASS", "message": "", "elements": [], "images": [], "checked_elements": []}
    activity.get(webdriver_instance)

    def on_element_lost():
        print("Element lost")
        return None

    def is_visible(elem: Element):
        element = elem.get_element(webdriver_instance)
        return element and element.size["width"] * element.size["height"] > 0 and element.is_displayed()

    images = [
        img
        for img in element_locator.get_all_of_type(webdriver_instance, element_types=["img"])
        if img.safe_operation_wrapper(is_visible, on_element_lost)
    ]

    counter = 1
    for obj in images:
        print(f"\rFound images {counter}", end="", flush=True)
        file = get_image_element(webdriver_instance, obj)

        if wont_read_or_rgba(file):
            print("force_screenshot")
            file = get_image_element(webdriver_instance, obj, force_screenshot=True)

        filename = file.name
        histogram = colors_histogram(filename)
        objects = yolo_opencv.object_detection(filename)
        text, rectangles, shape_img = get_text_from_image(filename)
        if text is None:
            return {"status": "NOTRUN", "message": "Tesseract was not installed and/or added to PATH"}
        file.close()
        counter += 1
        conclusion["images"].append(
            {
                "element": obj,
                "text": text,
                "rectangles": rectangles,
                "shape": shape_img,
                "histogram": histogram,
                "objects": objects,
            }
        )
    print(f"dependency timer = {time.time() - time1}")
    return conclusion
