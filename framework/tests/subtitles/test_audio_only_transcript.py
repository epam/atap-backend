from selenium import webdriver

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.libs.is_visible import is_visible
from framework.tests.subtitles.lib import elements_with_media, check_for_description, elements_activate_audio

name = '''Ensures that audio elements have transcripts'''
WCAG = '1.2.5'
framework_version = 5
webdriver_restart_required = True

elements_type = "audio"
test_data = [
    {
        "page_info": {
            "url": "subtitles/page_audio_transcript_ok.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "subtitles/page_audio_transcript_ok_2.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "subtitles/page_audio_transcript_fail.html"
        },
        "expected_status": "FAIL"
    }
]


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """
    Test for checking whether audio content has transcript.
    Refers to WCAG 2.0 1.2.5.
    Returns test result as a dict:
    result = {
                'status': <'ERROR', 'PASS', 'NOELEMENTS' or 'NOTRUN'>,
                'message': <string>,
                'elements': [{'source': Element, 'problem': <string>, 'error_id': <error_id>}, etc.],
                'checked_elements': [<element1>, <element2>, ...],
             }
    """
    activity.get(webdriver_instance)
    result = {'status': 'PASS', 'message': '', 'elements': [], 'checked_elements': []}
    audios = elements_with_media(webdriver_instance, element_locator, ['object', 'embed', 'iframe', 'a', 'video'], 'audio')
    native_audios = element_locator.get_all_of_type(webdriver_instance, ['audio'])
    audios += native_audios
    audios += elements_activate_audio(webdriver_instance, element_locator, native_audios)

    result['checked_elements'] = audios
    if result['checked_elements']:
        counter = 1

        def check_audio(audio: Element):
            if audio.tag_name != 'audio':
                # audio element shouldn't be visible
                if not is_visible(audio, webdriver_instance):
                    return
            nonlocal counter
            print(f'Check audio {counter}: {audio}')
            counter += 1
            if not check_for_description(element_locator, webdriver_instance, audio, 'audio', ['transcript']):
                result['elements'].append(
                    {'element': audio, 'problem': 'Audio content seems to be without transcript.', 'severity': "FAIL"})
        Element.safe_foreach(audios, check_audio)
        if result['elements']:
            result['status'] = 'FAIL'
            result['message'] = 'Found audio elements without transcript'
    else:
        result['status'] = 'NOELEMENTS'
    print(result)
    return result
