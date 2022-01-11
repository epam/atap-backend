from collections import defaultdict
from typing import List

from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

from framework.element import Element
from framework.element_locator import ElementLocator


def check_image_contain_dot(x_image: int, y_image: int, w_image: int, h_image: int, dot: tuple) -> bool:
    return x_image <= dot[0] <= x_image + w_image and y_image <= dot[1] <= y_image + h_image


def check_image_contain_elem(
        x_image: int, y_image: int, w_image: int, h_image: int, x_elem: int, y_elem: int, w_elem: int, h_elem: int
) -> bool:
    dots = (
        (x_elem, y_elem),
        (x_elem, y_elem + h_elem),
        (x_elem + w_elem, y_elem + h_elem),
        (x_elem + w_elem, y_elem)
    )
    for dot in dots:
        if not check_image_contain_dot(x_image, y_image, w_image, h_image, dot):
            return False
    return True


def find_background_images(element_locator: ElementLocator, driver: RemoteWebDriver, images: List[dict]) -> list:
    """looking for such pictures, which are other elements"""

    def on_element_lost() -> tuple:
        return None, None

    def get_location_and_size(element: Element) -> tuple:
        web_element = element.get_element(driver)
        return web_element.location, web_element.size

    all_elements = element_locator.get_all_by_xpath(driver, '//body//*[not(*)]')
    elements = defaultdict(dict)
    for i, elem in enumerate(all_elements):
        elem_location, elem_size = elem.safe_operation_wrapper(get_location_and_size, on_element_lost)
        elements[i] = {'elem': elem,
                       'location': elem_location,
                       'size': elem_size}

    background_images = []
    for i, img in enumerate(images):
        image = img['element']
        print(f'\rChecking background images {i+1}/{len(images)}', end='', flush=True)

        image_location, image_size = image.safe_operation_wrapper(get_location_and_size, on_element_lost)
        if image_location is None or image_size is None:
            continue
        h_image = image_size['height']
        if not h_image:
            continue
        for elem_spec in elements.values():
            elem = elem_spec['elem']
            elem_location, elem_size = elem_spec['location'], elem_spec['size']
            h_elem = elem_size['height']
            if elem != image and h_elem and check_image_contain_elem(image_location['x'], image_location['y'],
                                                                     image_size['width'], h_image, elem_location['x'],
                                                                     elem_location['y'], elem_size['width'], h_elem):
                background_images.append(image)
                break
    return background_images
