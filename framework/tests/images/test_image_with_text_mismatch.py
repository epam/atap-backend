from selenium import webdriver
from pylev import levenshtein

from framework.libs.descriptions import get_description_image
from framework.libs.clean import clean_text

from framework.element_locator import ElementLocator
from framework.element import Element

from .test_images_of_text import collect_images_of_text


name = "Ensures that <img> element with text has text description that matches the text in the image"
depends = ["test_images_of_text"]
webdriver_restart_required = False
framework_version = 5
WCAG = "2.5.3"
elements_type = "image"
test_data = [
    {"page_info": {"url": "images/page_bug_image_with_text_m.html"}, "expected_status": "FAIL"},
    {"page_info": {"url": "images/page_bug_image_with_text_m_2.html"}, "expected_status": "FAIL"},
    {"page_info": {"url": "images/page_good_image_with_text.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "images/page_good_image_with_text_m_4.html"}, "expected_status": "PASS"},
]

THRESHOLD_FOR_DISTANCE_BETWEEN_WORDS = 0.8


def levenshtein_distance(sequence, word):
    print("\nlevenshtein_distance", sequence, word)
    capacity = len(sequence) + len(word)

    print("distance", (capacity - levenshtein(sequence, word)) / capacity)
    return (capacity - levenshtein(sequence, word)) / capacity


def alt_and_text_similarity(text, alternative_text):
    """
    Compares OCR-fetched text from image with its full programmatic description - alternative text.

    Args:
        text (list): collection of recognized "words"
        alternative_text (str): string of alt, caption, aria-* etc

    Returns:
        bool: text and alternative matches
    """
    print("\nalt_and_text_similarity")
    print("text", text)
    words = clean_text(" ".join(text), False).lower().split()  # * alphanumeric only
    print("clean text", words)
    alternative_text = alternative_text.split(" ")
    print("alt", alternative_text)
    words = [*filter(None, words)]

    # ? skips empty alt
    match_amount = sum(
        any(
            levenshtein_distance(word, word_alt) >= THRESHOLD_FOR_DISTANCE_BETWEEN_WORDS
            for word_alt in alternative_text
        )
        for word in words
    )

    print("\nmatch_amount / len(words)", match_amount / len(words))

    return match_amount / len(words) >= 0.75


def status_result(checked, failed):
    result = {
        "status": "PASS",
        "message": "Visual text matches description for all images.",
        "elements": [],
        "checked_elements": checked,
        "dependency": {},
    }

    if failed:
        result["status"] = "FAIL"
        result["message"] = "Visual text on images is not associated programmatically."
        result["elements"] = [
            {
                "element": img,
                "problem": "Text on image and from its description do not match.",
                "severity": "FAIL",
                "error_id": "TextMismatchImage",
            }
            for img in failed
        ]
        result["dependency"] = failed

    return result


def collect_mismatched_images(images_of_text, driver):
    """
    Retries OCR for dependency images with high resolution and adjusted settings, saves recognized

    Returns:
        tuple: new OCR-fetched text images, images that failed WCAG
    """
    text_images, text_descriptions = collect_images_of_text(
        images_of_text, driver, save_text=True, large_image=True
    )

    mismatched_images = []

    def verify_programmatic_text(image_of_text):
        print("\nverify_programmatic_text")
        nonlocal mismatched_images

        image, text = image_of_text
        print("image, text", image, "\n", text)
        description = image_description(image, driver)
        print("\ndescription", description)

        # * too straightforward
        # if check_formula_in_image(text):
        # return

        if not alt_and_text_similarity(text, description):
            print("\nappend mismatched", image)
            mismatched_images.append(image)

    if len(text_images) < len(images_of_text):
        print("\nWRONG DEPENDENCY FOR IMAGES", [*set(images_of_text).difference(text_images)])

    Element.safe_foreach([*zip(text_images, text_descriptions)], verify_programmatic_text)

    return text_images, mismatched_images


def image_description(image, driver):
    """
    alt, aria-label, aria-labelledby, aria-describedby, id, title, figcaption, longdesc

    Returns:
        str || dict: get_description_image from descriptions.py
    """
    print("\nimage_description")
    body = Element(driver.find_element_by_tag_name("body"), driver)

    return get_description_image(driver, image, body)


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator, dependencies):
    activity.get(webdriver_instance)

    images_of_text = [dep.get("element") for dep in dependencies[depends[0]].get("elements")]

    if not images_of_text:
        return {
            "status": "NOELEMENTS",
            "message": "There are no images of text for testing.",
            "elements": [],
            "checked_elements": [],
        }

    images, mismatched = collect_mismatched_images(images_of_text, webdriver_instance)
    result = status_result(images, mismatched)

    print("***********************************************RESULT***********************************************")
    print(result)
    return result
