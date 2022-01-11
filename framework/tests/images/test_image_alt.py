import re
import string

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from framework.libs.check_grammar import check_grammar
from framework.element import Element, JS_BUILD_CSS_SELECTOR
from framework.element_locator import ElementLocator

WCAG = "1.1.1"
framework_version = 5
locator_required_elements = ["img"]
name = "Ensures that all images have meaningful text alternatives"
webdriver_restart_required = False
elements_type = "image"
test_data = [
    {"page_info": {"url": "images/fast_image_alt/page_good.html"}, "expected_status": "PASS"},
    {
        "page_info": {"url": "images/fast_image_alt/page_bug.html"},
        "expected_status": "FAIL",
        "expected_additional_content_length": {"elements": 11},
    },
]


STOP_WORDS = [
    "new",
    "header",
    "image",
    "spacer",
    "picture",
    "alt",
    "alternative",
    "text",
    "scene",
    "photo",
    "intro",
    "slide",
    "description",
    "img",
]

EXPANSIONS = [
    ".jpg",
    ".png",
    ".gif",
    ".tif",
    ".tiff",
    ".bmp",
    ".jpeg",
    ".eps",
    ".raw",
    ".cr2",
    ".nef",
    ".orf",
    ".sr2",
]


def delete_punctuation(s: str):
    return s.translate(str.maketrans("", "", string.punctuation))


def meaningful_vocabulary(sentence):
    return re.findall("[\w'\.`_\-@/\\|]+", sentence)


def replace_stop_words(vocabulary):
    return [word for word in vocabulary if word not in STOP_WORDS]


def is_empty(sentence):
    return not bool(re.sub("\s*", "", sentence))


def is_filename(vocabulary):
    filenames = [
        word for word in vocabulary if [*filter(lambda exp, word=word: re.match(f".*\{exp}", word), EXPANSIONS)]
    ]

    return 1 <= len(filenames) >= len(vocabulary) - 1  # * only filename or one with one other word


def is_gibberish(vocabulary):
    return not [
        word for word in vocabulary if re.match(".*[A-Za-z]{3,}.*", word)
    ]  # * more than 3 latin letter in a row


def alt_is_not_valid(alt):
    """
    Example
    alt = 'alternative text42 for cat-33.png image number 2 of 89examples; another? beautiful! 100 k b s collage'
    alt_words = ['text42', 'for', 'cat-33.png', 'number', '2', 'of', '89examples', 'another', 'beautiful', '100', 'k', 'b', 's', 'collage']
    is_filename(["cat-33.png", "instance"]) -> True
    is_gibberish(["tx42", "2", "of@", "100,", "k!", "b?", "s"]) -> True
    check_grammar(alt_words) = ['text42', 'cat-33.png', '2', '89examples', '100', 'k', 'b', 's']

    Args:
        alt (str): image alt
    """

    alt_words = replace_stop_words(meaningful_vocabulary(alt.lower()))

    return (
        is_empty(alt)
        or is_gibberish(alt_words)
        or is_filename(alt_words)
        or sum(any(i.isdigit() for i in w) and any(i.isalpha() for i in w) for w in alt_words) / len(alt_words)
        > 0.8  # ? large amount of cat2 or hero53aimer like words
    )


def check_image_alt(image: Element):
    print(f"\rAnalyzing images {test.images.index(image) + 1}/{len(test.images)}", end="", flush=True)

    alt = image.get_attribute(test.driver, "alt")
    # * empty alt is allowed
    if alt is None or not alt:
        return

    if alt_is_not_valid(alt.lower()):
        test.failed_images.append(
            {
                "element": image,
                "problem": "Failure of Success Criterion 1.1.1 and 1.2.1 due to using text alternatives that are not "
                "alternatives (e.g., filenames or placeholder text)."
                "https://www.w3.org/TR/2016/NOTE-WCAG20-TECHS-20161007/F30.",
                "severity": "FAIL",
            }
        )
    else:
        # * delete punctuation and drop words of punctuation
        words = [*filter(None, [delete_punctuation(w).strip() for w in meaningful_vocabulary(alt.lower())])]
        wrong_grammar_words = check_grammar(words)  # * disable "if not w.isdigit()""

        # * grammar failed word amount is large
        if alt and (len(alt) <= 3 or len(wrong_grammar_words) / len(words) > 0.22):
            test.failed_images.append(
                {"element": image, "problem": "Grammar mistake or very short message", "severity": "WARN"}
            )


def no_elements_status():
    return {
        "status": "NOELEMENTS",
        "message": "There are no images for testing.",
        "elements": [],
        "checked_elements": [],
    }


def result_status(elements, failed=[]):
    result = {
        "status": "PASS",
        "message": "All img elements have alt without filenames or placeholder text.",
        "elements": failed,
        "checked_elements": elements,
    }
    if failed:
        result["status"] = "FAIL"
        result["message"] = "Images with bad alternative text(e.g., filenames or placeholder text) were found."

    return result


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)

    test.driver = webdriver_instance
    test.images, test.failed_images = [], []
    web_image_paths = webdriver_instance.execute_script(
        f"""
            function buildSelector() {{
                {JS_BUILD_CSS_SELECTOR}
            }}

            return [...document.images].map(img => buildSelector(img));
        """
    )

    for selector in web_image_paths:
        try:
            # * some images could be updated in carousel, so webelements will be stale
            # * still screenshots do not perform duplicates
            print("*************************")
            print("wait up to 5 s")
            img = WebDriverWait(webdriver_instance, 5).until(
                presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            test.images.append(Element(img, webdriver_instance))
        except TimeoutException:
            print(f"Timeout reaching\t{selector}")

    if not test.images:
        return no_elements_status()

    Element.safe_foreach(test.images, check_image_alt)

    result = result_status(test.images, failed=test.failed_images)
    print(result)
    return result
