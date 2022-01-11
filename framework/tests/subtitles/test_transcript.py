from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.is_visible import is_visible
from framework.libs.hide_cookie_popup import hide_cookie_popup
from framework.tests.subtitles.lib import elements_with_media, AUDIO_FILE_FORMATS, find_description_button

name = '''Ensures that video and audio elements have transcripts'''
WCAG = '1.2.5'
framework_version = 0
webdriver_restart_required = False

elements_type = "video"
test_data = [
    {
        "page_info": {
            "url": "page_transcript_ok.html"
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


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """
    Test for checking whether pre-recorded video content has audio description.
    Refers to WCAG 2.0 1.2.5.
    ATTENTION: the test does not cover functionality of similar axE tests, but expands them.
    Returns test result as a dict:
    result = {
                'status': <'ERROR', 'PASS' or 'NOTRUN'>,
                'message': <string>,
                'elements': [{'source': Element, 'problem': <string>, 'error_id': <error_id>}, etc.],
                'checked_elements': [<element1>, <element2>, ...],
             }
    """
    result = {'status': 'PASS',
              'message': '',
              'elements': [],
              'checked_elements': []}

    activity.get(webdriver_instance)
    hide_cookie_popup(webdriver_instance, activity)

    videos = elements_with_media(webdriver_instance, element_locator, ['object', 'embed', 'iframe'], 'video')
    videos += element_locator.get_all_of_type(webdriver_instance, ['video'])
    audios = element_locator.get_all_of_type(webdriver_instance, ['audio'])

    result['checked_elements'] = videos + audios
    if videos or audios:
        counter = 1

        def check_video(video):
            nonlocal counter
            print(f'Check video {counter}: {video}')
            counter += 1
            if not check_for_transcript(webdriver_instance, video):
                result['elements'].append({'element': video,
                                           'problem': 'Video content seems to be without transcript.',
                                           'severity': "FAIL" if is_visible(video, webdriver_instance) else "WARN"})

        def check_audio(audio):
            nonlocal counter
            print(f'Check audio {counter}: {audio}')
            counter += 1
            if not check_for_transcript(webdriver_instance, audio):
                result['elements'].append({'element': audio,
                                           'problem': 'Audio content seems to be without transcript.',
                                           'severity': "FAIL" if is_visible(audio, webdriver_instance) else "WARN"})

        Element.safe_foreach(videos, check_video)
        Element.safe_foreach(audios, check_audio)

        if result['elements']:
            result['status'] = 'FAIL'
            result['message'] = 'Found video/audio elements without transcript'

    else:
        result['status'] = 'NOELEMENTS'

    print(result)
    return result


def check_for_transcript(driver: webdriver.Firefox, element: Element):
    """
    Checks if video content has descriptions.
    Return True if descriptions exist, otherwise returns False.
    """

    if element.tag_name == 'video':
        children = element.find_by_xpath("*", driver)
        children = [child for child in children if
                    child.tag_name == 'track' and child.get_attribute(driver, 'kind')]
        for child in children:
            src = child.get_attribute(driver, 'src')
            if any(audio_file_format in src for audio_file_format in AUDIO_FILE_FORMATS):
                # was it intentional? or should it be `src.endswith(audio_file_format)`?
                return children
        return find_description_button(driver, element, 'video', 'transcript')
    else:
        source = element.get_attribute(driver, 'data') if element.tag_name == 'object' \
            else element.get_attribute(driver, 'src')
        current_window = driver.current_window_handle
        driver.execute_script(f"window.open('{source}')")
        driver.switch_to.window(driver.window_handles[-1])
        try:
            video_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
        except TimeoutException:
            driver.close()
            driver.switch_to.window(current_window)
            return False

        children = video_element.find_elements_by_css_selector("*")
        children = [child for child in children if child.tag_name == 'track' and child.get_attribute('kind')]
        for child in children:
            src = child.get_attribute(driver, 'src')
            if any(audio_file_format in src for audio_file_format in AUDIO_FILE_FORMATS):
                # was it intentional? or should it be `src.endswith(audio_file_format)`?
                driver.close()
                driver.switch_to.window(current_window)
                return children
        driver.close()
        driver.switch_to.window(current_window)
        return False
