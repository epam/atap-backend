from selenium import webdriver

from framework.element_locator import ElementLocator


WCAG = '2.5.3'
framework_version = 5
depends = ["test_link_image_nonTextName"]
webdriver_restart_required = False
name = 'Ensures that labels for image links contain the text that is presented visually'
elements_type = "image"
test_data = [
    {
        "page_info": {
            "url": "link_image/page_good_link_image_3.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "link_image/page_bugs_link_image_3.html"
        },
        "expected_status": "FAIL"
    }
]


def link_descr_and_image_descr_have_same_purpose(link_description, image_description):
    link_descr_words = set().union(*(string.split() for string in link_description))
    image_descr_words = set().union(*(descr.split() for descr in image_description.values()))
    return len(link_descr_words.intersection(image_descr_words)) > 0


def one_description_included_other(descr, other_descr):
    for first_word, second_word in zip(other_descr[:-1], other_descr[1:]):
        if (first_word + ' ' + second_word) not in descr:
            return False
    return True


def check_wcag(link_description, image_description):
    if len(link_description) > 1 or len(image_description) > 1:
        return True
    return (one_description_included_other(link_description[0], list(image_description.values())[0].split()) or
            one_description_included_other(list(image_description.values())[0], link_description[0].split()))


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator, dependencies):
    conclusion = {'status': "PASS", 'message': '', 'elements': [], 'checked_elements': []}
    if not dependencies['test_link_image_nonTextName']['elements_with_description']:
        conclusion['status'] = 'NOELEMENTS'
        return conclusion

    conclusion['checked_elements'].extend([elem['element'] for elem in
                                           dependencies['test_link_image_nonTextName']['elements_with_description']])
    for elem in dependencies['test_link_image_nonTextName']['elements_with_description']:
        if elem['link_descr'] and elem['image_descr'] and \
                link_descr_and_image_descr_have_same_purpose(elem['link_descr'], elem['image_descr']) and \
                not check_wcag(elem['link_descr'], elem['image_descr']):
            conclusion["elements"].append({"element": elem['element'],
                                           "problem": "Failure due to the accessible name not containing the visible "
                                                      "label text",
                                           "error_id": 'Mismatch'})
    if conclusion['elements']:
        conclusion['status'] = 'FAIL'
    return conclusion