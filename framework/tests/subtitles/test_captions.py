from selenium import webdriver

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.is_visible import is_visible
from framework.tests.subtitles.lib import elements_with_media, find_description_button

name = '''Ensures that audio and video elements have transcripts'''
framework_version = 0
WCAG = '1.2.2'
webdriver_restart_required = False

elements_type = "video"
test_data = [
    {
        "page_info": {
            "url": "page_captions_ok.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_transcript_fail.html"
        },
        "expected_status": "FAIL"
    }
]

VIDEO = ['.mp4', '.webm', '.mov']
AUDIO = ['.mp3', '.wav', '.ogg', '.aif', '.aiff', '.vff', '.vtt']


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """
    Test for checking whether pre-recorded media content (audio or video) has captions.
    Refers to WCAG 2.0 1.2.2.
    ATTENTION: test does not cover functionality of similar axE tests, but expands them.
    Returns test result as a dict:
    result = {
                'status': <'ERROR', 'PASS' or 'NOTRUN'>,
                'message': <string>,
                'elements': [{'source': Element, 'problem': <string>, 'error_id': <error_id>}, etc.],
                'checked_elements': [<element1>, <element2>, ...]
             }
    """
    result = {'status': 'PASS',
              'message': '',
              'elements': [],
              'checked_elements': []}

    activity.get(webdriver_instance)

    videos = elements_with_media(webdriver_instance, element_locator, ['object', 'embed', 'iframe'], 'video')
    videos += element_locator.get_all_of_type(webdriver_instance, ['video'])
    audios = elements_with_media(webdriver_instance, element_locator, ['object', 'embed', 'iframe'], 'audio')
    audios += element_locator.get_all_of_type(webdriver_instance, ['audio'])
    result['checked_elements'] = videos + audios

    if videos or audios:

        def check_video(video):
            if not check_for_captions(webdriver_instance, video, 'video'):
                result['elements'].append({'element': video,
                                           'problem': 'Video content seems to be without captions.',
                                           'severity': "FAIL" if is_visible(video, webdriver_instance) else "WARN"})
            activity.get(webdriver_instance)

        def check_audio(audio):
            if not check_for_captions(webdriver_instance, audio, 'audio'):
                result['elements'].append({'element': audio,
                                           'problem': 'Audio content seems to be without captions.',
                                           'severity': "FAIL" if is_visible(audio, webdriver_instance) else "WARN"})
            activity.get(webdriver_instance)

        Element.safe_foreach(videos, check_video)
        Element.safe_foreach(audios, check_audio)

        if result['elements']:
            result['status'] = 'FAIL'

    else:
        result['status'] = 'NOELEMENTS'

    print(result)
    return result


def check_for_captions(driver: webdriver.Firefox, element: Element, media):
    """
    Checks if media content has captions.
    Parameter 'media' sets the type of media content and is expected as 'audio' or 'video'.
    Return True if captions exist, otherwise returns False.
    """

    if element.tag_name == 'video' or element.tag_name == 'audio':
        children = element.find_by_xpath("*", driver)
        children = [child for child in children if child.tag_name == 'track' and
                    child.get_attribute(driver, 'kind')]
        return children or find_description_button(driver, element, media, 'captions')  # FIXME!
    elif element.tag_name == 'object':
        driver.get(element.get_attribute(driver, 'data'))
    else:
        driver.get(element.get_attribute(driver, 'src'))
    source = driver.find_element_by_tag_name(media)
    children = source.find_elements_by_css_selector("*")

    return [child for child in children if child.tag_name == 'track' and child.get_attribute(driver, 'kind')]
