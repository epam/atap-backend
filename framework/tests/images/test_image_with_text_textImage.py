from selenium import webdriver
import time


from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs import clean

name = "Ensures that <img> elements with text don't contain formula or text only"
depends = ["test_dependency_for_image"]
webdriver_restart_required = False
framework_version = 0
WCAG = '1.4.5'
elements_type = "image"
test_data = [
    {
        "page_info": {
            "url": "images/page_bug_image_with_text_tI.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "images/page_bug_image_with_text_tI_2.html"
        },
        "expected_status": "FAIL"
    },
    {
        "page_info": {
            "url": "images/page_good_image_with_text.html"
        },
        "expected_status": "PASS"
    }
]
MATH_SYMBOLS = '+-=*/%'


def check_formula_in_image(text: str) -> bool:
    counter_math_symbol = sum([int(text.count(symbol)) for symbol in MATH_SYMBOLS])
    return counter_math_symbol / len(clean.clean_text(text).replace(' ', '')) >= 0.15


def calculate_area_of_text(rectangles: list, shape: list):
    if len(rectangles) < 2:
        return 100 * rectangles[0].h * rectangles[0].w / (shape[0] * shape[1])
    rectangles = [r for r in rectangles if len([other for other in rectangles if r is not other and r > other]) == 0]
    x_coords = sorted(sum([[x.dots[0][0], x.dots[2][0]] for x in rectangles], []))
    y_coords = sorted(sum([[x.dots[0][1], x.dots[2][1]] for x in rectangles], []))
    if x_coords and y_coords:
        return 100 * abs(x_coords[0] - x_coords[-1]) * abs(y_coords[0] - y_coords[-1]) / (shape[0] * shape[1])
    else:
        return 0


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    time1 = time.time()
    activity.get(webdriver_instance)
    conclusion = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': []}
    images = dependencies['test_dependency_for_image']['images']

    if not images:
        conclusion['status'] = 'NOELEMENTS'
        return conclusion
    counter = 1

    def check_image(obj):
        nonlocal counter
        print(f'\rAnalyzing elements {counter}/{len(images)}', end="", flush=True)
        counter += 1
        conclusion['checked_elements'].append(obj['element'])
        text = obj['text']
        if not text:
            return

        if check_formula_in_image(text):
            conclusion["elements"].append({"element": obj['element'],
                                           "problem": "Error: This picture contains the formula. It is desirable to "
                                                      "make the formula text or special MathJax characters"})
            return

        if (obj['rectangles'] is not None and obj['shape'] is not None and
                calculate_area_of_text(obj['rectangles'], obj['shape']) > 25):
            conclusion["elements"].append({"element": obj['element'],
                                           "problem": "Error: this picture consists of text only - WCAG 1.4.5 bug."})
            return

    Element.safe_foreach(images, check_image)
    if conclusion['elements']:
        conclusion["status"] = "FAIL"
    print(f"test_image_with_text_textImage timer = {time.time() - time1}")
    return conclusion
