from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException, WebDriverException

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.distance_between_elements import distance
from framework.libs.is_visible import is_visible

import time
from typing import List, Optional

VIDEO_FILE_FORMATS = ['.mp4', '.webm', '.mov']
AUDIO_FILE_FORMATS = ['.mp3', '.wav', '.ogg', '.aif', '.aiff', '.vff', '.vtt']


def find_media_element_in_frame(driver: webdriver.Firefox, iframe: Element, locator: str, by=By.TAG_NAME, many=False):
    switch_to_iframe(driver, iframe)
    try:
        if many:
            return WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((by, locator)))
        else:
            return WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, locator)))
    except TimeoutException:
        return None
    finally:
        revert(driver)


def find_media_element_in_window(driver, element, media, source=None):
    current_window = switch_to_window(driver, element, source)
    try:
        return WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, media)))
    except (TimeoutException, NoSuchWindowException):
        return None
    finally:
        revert(driver, current_window)


def switch_to_iframe(driver: webdriver.Firefox, iframe: Element) -> None:
    # TODO: Why not make a context manager from this function
    #  if it is necessary to call `revert` function after calling this?
    # @contextmanager
    # def switch_to_iframe_with_context(driver: webdriver.Firefox, iframe: Element) -> Generator[None, None, None]:
    #     try:
    #         driver.switch_to.frame(iframe.get_element(driver))
    #         yield
    #     finally:
    #         revert(driver)
    driver.switch_to.frame(iframe.get_element(driver))


def switch_to_window(driver: webdriver.Firefox, element: Element, source: Optional[str] = None):
    current_window = driver.current_window_handle
    if source is None:
        attribute = 'data' if element.tag_name == 'object' else ('href' if element.tag_name == 'a' else 'src')
        source = element.get_attribute(driver, attribute)
    driver.execute_script(f"window.open('{source}')")
    driver.switch_to.window(driver.window_handles[-1])
    return current_window


def revert(driver: webdriver.Firefox, window=None) -> None:
    if window is not None:
        try:
            driver.close()
        except NoSuchWindowException:
            pass
        finally:
            driver.switch_to.window(window)
    else:
        driver.switch_to.default_content()
    time.sleep(2)


def elements_with_media(driver: webdriver.Firefox, element_locator: ElementLocator, tags: List[str], media: str):
    """
    Detects elements containing media(video or audio).
    Elements are chosen via its tag, which is set by user in 'tag' parameter.
    Returns list of objects with video/audio.
    """

    elements = element_locator.get_all_of_type(driver, tags)
    result = []

    def check_for_media(element: Element):
        if media == 'audio' and element.tag_name == 'video':
            source = element.find_by_xpath('child::source', driver)
            src = source[0].get_attribute(driver, 'src')
            type_ = source[0].get_attribute(driver, 'type')
            if (src is not None and any(audio_file_format in src for audio_file_format in AUDIO_FILE_FORMATS)) or (
                    type_ is not None and media in type_):
                result.append(element)
            return
        attribute = 'data' if element.tag_name == 'object' else ('href' if element.tag_name == 'a' else 'src')
        source = element.get_attribute(driver, attribute)
        if source is None:
            return
        if media == 'video' and any(video_file_format in source for video_file_format in VIDEO_FILE_FORMATS):
            result.append(element)
        elif media == 'audio' and any(audio_file_format in source for audio_file_format in AUDIO_FILE_FORMATS) and (
                element.tag_name != 'a' or media in element.source) and element.get_attribute(driver,
                                                                                              'download') is None:
            result.append(element)
        elif element.tag_name == 'iframe':
            if find_media_element_in_frame(driver, element, media) is not None:
                result.append(element)
            elif media == 'audio':
                scripts = find_media_element_in_frame(
                    driver, element, locator=f'//script[contains(@outerHTML, {media})]', by=By.XPATH, many=True)
                if scripts is not None:
                    switch_to_iframe(driver, element)
                    for script in scripts:
                        if media in script.get_attribute("outerHTML").lower():
                            result.append(element)
                            break
                    revert(driver)
        elif (source.startswith('http') or source.startswith('blob:http') or source.startswith('//')) and element.tag_name != 'a':
            if find_media_element_in_window(driver, element, media, source) is not None:
                result.append(element)

    Element.safe_foreach(elements, check_for_media)
    return result


def elements_activate_audio(driver: webdriver.Firefox, element_locator: ElementLocator, audios: List[Element]):
    result = []
    activators = element_locator.get_all_of_type(driver, ['a', 'button', 'svg'])

    def check_audio(audio: Element):
        audio = audio.get_element(driver)
        activator: Element
        for activator in activators:
            if 'play' not in activator.source or not is_visible(activator, driver):
                continue
            player = activator.get_element(driver)
            source_before_click = audio.get_attribute('outerHTML')
            driver.execute_script(
                f"window.scrollTo(0, {player.location['y'] - 0.5 * driver.get_window_size()['height']})")
            time.sleep(1)
            try:
                player.click()
            except WebDriverException:
                continue
            time.sleep(1)
            if audio.get_attribute('outerHTML') != source_before_click:
                result.append(activator)

    Element.safe_foreach(audios, check_audio)
    return result


def find_hidden_button(driver: webdriver.Firefox, element: Element, media_element: Element):
    """
    Checks a hidden button that could not be clicked, but it is performed using the 'button'/'a' tags and is located
    next to the media element being checked
    """
    clickable_tags = ['button', 'a']
    element = element if element.tag_name in clickable_tags else (
        element.get_parent(driver) if element.get_parent(driver).tag_name in clickable_tags else None)
    if element is None:
        return False
    return located_next_to(driver, media_element, element)


def check_that_description_appeared(driver: webdriver.Firefox, button: Element, kinds: List[str]) -> bool:
    """
    Check that the description of media content appears(or becomes visible) after clicking on the button in the home
    """
    elements_before_click = [x.get_attribute("outerHTML") for x in driver.find_element_by_tag_name(
        'body').find_elements_by_xpath('descendant::*')]
    button.get_element(driver).click()
    time.sleep(1)
    elements_after_click = driver.find_element_by_tag_name('body').find_elements_by_xpath('descendant::*')
    for element in elements_after_click:
        if element.get_attribute("outerHTML") not in elements_before_click and is_visible(element, driver):
            for kind in kinds:
                if element.text.lower().find(kind) != -1:
                    return True
    return False


def located_next_to(driver: webdriver.Firefox, element_1: Element, element_2: Element):
    """
    Checks that elements are close to each other visually or in the house(have a common ancestor)
    """
    return distance(driver, element_1, element_2) < 50 or set(element_1.find_by_xpath(
        'ancestor::*', driver)[-4:]).intersection(element_2.find_by_xpath('ancestor::*', driver)[-4:])


def get_elements_by_text_without_parents(locator: ElementLocator, driver: webdriver.Firefox, texts: List[str]) -> List[
    Element]:
    description_elements = []
    for text in texts:
        description_elements += locator.get_all_by_xpath(
            driver,
            f"//*[contains(text(), '{text}') or contains(text(), '{text.capitalize()}')]"
        )
        if text == 'captions':
            description_elements += locator.get_all_by_xpath(
                driver,
                f"//*[contains(@title, '{text}') or contains(@aria-label, '{text}') or "
                f"contains(@title, '{text.capitalize()}') or contains(@aria-label, '{text.capitalize()}')]"
            )
    return description_elements


def get_elements_with_text(locator: ElementLocator, driver: webdriver.Firefox, texts: List[str]) -> List[Element]:
    """
    Search for elements by text (and by the value of the title/aria-label attributes for captions)
    """
    description_elements = []
    for text in texts:
        description_elements += locator.get_all_by_xpath(
            driver,
            f"//*[contains(normalize-space(), '{text}') or contains(normalize-space(), '{text.capitalize()}')]"
        )
        if text == 'captions':
            description_elements += locator.get_all_by_xpath(
                driver,
                f"//*[contains(@title, '{text}') or contains(@aria-label, '{text}') or "
                f"contains(@title, '{text.capitalize()}') or contains(@aria-label, '{text.capitalize()}')]"
            )
    return description_elements


def any_element_is_visible_and_its_tag_is_header_or_p(driver: webdriver.Firefox,
                                                      description_elements: List[Element]) -> bool:
    description_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']
    return any(element.tag_name in description_tags and is_visible(element, driver) for element in description_elements)


def find_description_button(locator: ElementLocator, driver: webdriver.Firefox, media_element: Element, media: str,
                            kinds: List[str], description_elements: List[Element]) -> bool:
    """
    Looking for a button that, when clicked, opens a tab with the transcript/captions to the video.
    Signs: the element contains the text "transcript"/"captions", it is located near the video/audio element,
    clickable
    Return True if the button was found, otherwise False
    """

    for element in description_elements:
        if element.tag_name not in ['a', 'button']:
            continue
        for elem in [element, element.get_parent(driver)]:
            if located_next_to(driver, elem, media_element) and is_visible(elem, driver):
                action = elem.click(driver)['action']
                if action in ['NEWTAB', 'PAGECHANGE']:
                    return True
                elif action == 'NONE':
                    return check_that_description_appeared(driver, elem, kinds)
        if find_hidden_button(driver, element, media_element):
            return True
    if media_element.tag_name == 'iframe':
        driver.switch_to.frame(media_element.get_element(driver))
        try:
            media_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, media))
            )
            return find_description_button(locator, driver, Element(media_element, driver), media, kinds,
                                           get_elements_with_text(locator, driver, kinds))
        except TimeoutException:
            return False
        finally:
            driver.switch_to.default_content()
    return False


def check_description_for_native_media_elements(locator: ElementLocator, driver: webdriver.Firefox, element: Element,
                                                media: str, kinds: List[str]):
    """
    Checks for a description (transcript/captions) for a native media element (with the 'video' or 'audio' tags)
    """
    # TODO: rename function
    children = element.find_by_xpath("*", driver)
    children = [child for child in children if child.tag_name == 'track' and child.get_attribute(driver, 'kind')]
    if 'transcript' in kinds:
        for child in children:
            src = child.get_attribute(driver, 'src')
            if any(audio_file_format in src for audio_file_format in AUDIO_FILE_FORMATS):
                return children
        description_elements = get_elements_with_text(locator, driver, kinds)
        return any_element_is_visible_and_its_tag_is_header_or_p(driver,
                                                                 description_elements) or find_description_button(
            locator, driver, element, media, kinds, description_elements)
    else:
        return children or find_description_button(
            locator, driver, element, media, kinds, get_elements_with_text(locator, driver, kinds))


def check_for_description(locator: ElementLocator, driver: webdriver.Firefox, element: Element, media: str,
                          kinds: List[str]):
    """
    Checks if video/audio content has descriptions(transcript or captions)
    Return True if descriptions exist, otherwise returns False.
    """
    if element.tag_name == 'video':
        return check_description_for_native_media_elements(locator, driver, element, media, kinds)

    if element.tag_name == 'audio':
        key_phrases = ['text version', 'transcript']
        description_elements = get_elements_by_text_without_parents(locator, driver, key_phrases)
        if not description_elements:
            return
        return \
            any_element_is_visible_and_its_tag_is_header_or_p(driver, description_elements) \
            or find_description_button(locator, driver, element, media, kinds, description_elements) \
            or check_description_for_native_media_elements(locator, driver, element, media, kinds)

    current_window = None
    if element.tag_name == 'iframe':
        media_element = find_media_element_in_frame(driver, element, media)
        if media_element is None:
            description_elements = get_elements_with_text(locator, driver, kinds)
            return any_element_is_visible_and_its_tag_is_header_or_p(driver,
                                                                     description_elements) or find_description_button(
                locator, driver, element, media, kinds, description_elements)
        else:
            switch_to_iframe(driver, element)
    else:
        media_element = find_media_element_in_window(driver, element, media)
        if media_element is None:
            description_elements = get_elements_with_text(locator, driver, kinds)
            return any_element_is_visible_and_its_tag_is_header_or_p(driver,
                                                                     description_elements) or find_description_button(
                locator, driver, element, media, kinds, description_elements)
        else:
            current_window = switch_to_window(driver, element)

    children = [child for child in media_element.find_elements_by_css_selector("*") if child.tag_name == 'track' and
                child.get_attribute('kind')]
    if 'transcript' in kinds:
        for child in children:
            src = child.get_attribute('src')
            if any(audio_file_format in src for audio_file_format in AUDIO_FILE_FORMATS):
                # was it intentional? or should it be `src.endswith(audio_file_format)`?
                revert(driver, current_window)
                return children
        revert(driver, current_window)
        description_elements = get_elements_with_text(locator, driver, kinds)
        return any_element_is_visible_and_its_tag_is_header_or_p(driver,
                                                                 description_elements) or find_description_button(
            locator, driver, element, media, kinds, description_elements)
    else:
        revert(driver, current_window)
        description_elements = get_elements_with_text(locator, driver, kinds)
        return (children or any_element_is_visible_and_its_tag_is_header_or_p(driver, description_elements)
                or find_description_button(locator, driver, element, media, kinds, description_elements))
