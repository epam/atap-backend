from selenium import webdriver
import time


from framework.element import Element
from framework.libs import background_images
from framework.libs import analyze_histogram
from framework.element_locator import ElementLocator


depends = ["test_dependency_for_image"]
name = "Ensures that <img> elements with a decorative function have 'role=presentation' or 'alt=""' attribute set"
WCAG = "1.1.1"
locator_required_elements = []
framework_version = 0
elements_type = "image"
test_data = [
    {
        "page_info": {
            "url": "decorative_image/page_bug_decorative_image.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "decorative_image/page_good_decorative_image.html"
        },
        "expected_status": "PASS"
    }
]


def find_sensory_images(driver, images, background_images):

    def on_element_lost():
        print("Element was lost")
        return None

    def check_image(image):
        if image is not background_images and image.get_attribute(driver, 'aria-labelledby') is None and \
                image.get_attribute(driver, 'aria-describedby') is None and \
                image.get_attribute(driver, "role") != 'button':
            return True
        return None

    def relative_size(element):
        size = element.get_element(driver).size
        window_size = driver.get_window_size()
        return max(100 * size['width'] / window_size['width'], 100 * size['height'] / window_size['height'])

    new_images = []
    for image in images:
        if image['element'].safe_operation_wrapper(check_image, on_element_lost) is not None:
            new_images.append(image)

    sensory_images = []
    for i, image in enumerate(new_images):
        print(f'\rChecking sensory images {i+1}/{len(new_images)}', end="", flush=True)
        histogram = analyze_histogram.analyze_histogram(image['histogram'])
        flag_object = 1
        flag_color = 1
        if len(image['objects']) > 1:
            flag_object = 0
        if histogram is not None and len(histogram) < 4:
            flag_color = 1

        size = image['element'].safe_operation_wrapper(relative_size, on_element_lost)

        if flag_object and flag_color and not image['text'] and size is not None and size > 20:
            sensory_images.append(image['element'])

    return sensory_images


def check_attribute(driver, decor_image):
    """check the absence / presence of attributes required to ignore the image screen reader
    https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/F38
    https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/H67

    """
    alt = decor_image.get_attribute(driver, "alt")
    role = decor_image.get_attribute(driver, "role")
    title = decor_image.get_attribute(driver, "title")
    if role == 'presentation':
        return True
    if alt is None:
        return False
    if not alt and not title:
        return True
    return False


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    time1 = time.time()
    activity.get(webdriver_instance)
    conclusion = {'status': "PASS",
                  'message': 'The test finds decorative images(they do not carry any meaning) and '
                             'checks that such images are not found by the screen reader.',
                  'elements': [],
                  'checked_elements': [],
                  'sensory': [],
                  'background': [],
                  }
    images = dependencies['test_dependency_for_image']['images']

    if not images:
        conclusion['status'] = 'NOELEMENTS'
        return conclusion

    background_img = background_images.find_background_images(
        element_locator,
        webdriver_instance,
        images
    )
    conclusion['background'].extend(background_img)

    sensory_images = find_sensory_images(
        webdriver_instance,
        images,
        background_img
    )
    conclusion['sensory'].extend(sensory_images)

    if not background_img and not sensory_images:
        conclusion['status'] = 'NOELEMENTS'
        return conclusion

    conclusion['checked_elements'].extend(background_img)
    conclusion['checked_elements'].extend(sensory_images)

    def check_background_image(image):
        if not check_attribute(webdriver_instance, image):
            conclusion["elements"].append({"element": image,
                                           "problem": "Error: this picture is decorative (background)."
                                                      "Incorrect attributes role/title/alt -> picture is not ignored "
                                                      "by the screen reader."})
    Element.safe_foreach(background_img, check_background_image)

    def check_sensory_image(image):
        if not check_attribute(webdriver_instance, image):
            conclusion["elements"].append({"element": image,
                                           "problem": "Error: this picture is decorative (sensory)."
                                                      "Incorrect attributes role/title/alt -> picture is not ignored " 
                                                      "by the screen reader."})
    Element.safe_foreach(sensory_images, check_sensory_image)

    if conclusion['elements']:
        conclusion["status"] = "FAIL"
    print(f"test_decorative_image timer = {time.time() - time1}")
    return conclusion
