from tempfile import NamedTemporaryFile
from cv2 import imread, imwrite, resize, IMREAD_UNCHANGED
import requests


def save_screen(element, driver):
    file = NamedTemporaryFile(delete=False, suffix=".png")
    element.get_element(driver).screenshot(file.name)

    im_width, im_height = driver.execute_script(
        "return [arguments[0].naturalWidth, arguments[0].naturalHeight];", element.get_element(driver)
    )

    image = imread(file.name, IMREAD_UNCHANGED)
    imwrite(file.name, resize(image, (im_width, im_height)))

    return file


def wont_read_or_rgba(image_file):
    cv_image = imread(image_file.name, IMREAD_UNCHANGED)

    return cv_image is None or len(cv_image.shape) == 3 and cv_image.shape[2] == 4


def get_image_element(driver, element, force_screenshot=False):
    """download this image or cut screen"""

    def on_element_lost():
        print("Element lost")

    def get_src(elem):
        return driver.execute_script("return arguments[0].src;", elem.get_element(driver))

    src = element.safe_operation_wrapper(get_src, on_element_lost)

    if force_screenshot:
        return save_screen(element, driver)

    if src is not None:
        if src.find(".svg") != -1:
            print("\nsrc svg")
            return save_screen(element, driver)

        try:
            file = NamedTemporaryFile(delete=False, suffix=".png")
            r = requests.get(src, stream=True, allow_redirects=False)
            if r.status_code == 200 and len(r.content):
                file.write(r.content)
                file.seek(0)
                return file
        except (
            requests.exceptions.MissingSchema,
            requests.exceptions.InvalidURL,
            requests.exceptions.InvalidSchema,
            requests.exceptions.ConnectionError,
        ) as exc:
            print("\nexception", exc)

    print("\nno source or src request returned an exception", save_screen)
    return save_screen(element, driver)
