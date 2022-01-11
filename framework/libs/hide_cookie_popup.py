import time
from framework import element
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException, StaleElementReferenceException

ACCEPT_BUTTON_TEXT = ["accept", "agree", "yes", "close", "принять"]
CLOSE_BUTTON_DATA = ["close"]
COOKIE_INFO_TEXT = ["cookie", "compliance with gdpr"]
ACCEPTABLE_BUTTON_TAG_NAMES = ["a", "input", "button"]


def __find_cookie_popup_recurse(element):
    try:
        element_list = element.find_elements_by_xpath("*")
        if len(element_list) == 0:
            return element
        element_list = reversed([el for el in element_list if el.tag_name not in ["script"]])
        for e in element_list:
            for keyword in COOKIE_INFO_TEXT:
                if keyword in e.get_attribute("innerHTML").lower():
                    result = __find_cookie_popup_recurse(e)
                    if result is not None:
                        return result
                    break
        return None
    except StaleElementReferenceException:
        return None


def _find_accept_button_recurse(element, max_depth=10, max_iterations_counter=None):
    if max_iterations_counter is None:
        max_iterations_counter = {
            "iterations": 0
        }
    if max_depth <= 0:
        return None
    try:
        if element.tag_name in ACCEPTABLE_BUTTON_TAG_NAMES:
            try:
                # print(f"Trying to click on {element.get_attribute('innerHTML')[:50]}")
                element.click()
                return element
            except (ElementNotInteractableException, ElementClickInterceptedException) as e:
                # print("clicking failed, continuing the search")
                return None
        element_list = element.find_elements_by_xpath("*")
        if len(element_list) == 0:
            return None
        element_list = [el for el in element_list if el.tag_name not in ["script"] and el != element]
        for e in element_list:
            max_iterations_counter["iterations"] += 1
            for keyword in ACCEPT_BUTTON_TEXT:
                if keyword in e.get_attribute("innerHTML").lower():
                    result = _find_accept_button_recurse(e, max_depth=max_depth-1, max_iterations_counter=max_iterations_counter)
                    if result is not None:
                        return result
                    break
            for keyword in CLOSE_BUTTON_DATA:
                if keyword in e.get_attribute("outerHTML").lower():
                    result = _find_accept_button_recurse(e, max_depth=max_depth-1, max_iterations_counter=max_iterations_counter)
                    if result is not None:
                        return result
                    break

            if max_iterations_counter["iterations"] > 200:
                print("Max iterations reached, assuming button not found")
                return None

        return None
    except StaleElementReferenceException:
        return None


def hide_cookie_popup(webdriver_instance, activity, target_element=None):
    try:
        element_was_visible = target_element is not None and target_element.is_displayed()
        # First, let's find the popup
        cookie_text_element = __find_cookie_popup_recurse(webdriver_instance.find_element_by_tag_name('html'))
        if cookie_text_element is None:
            print("No cookie popup detected")
            return False

        print("Cookies popup found, looking for button")
        # Next, find an element that looks like the accept button and click it
        element_to_search_from = cookie_text_element.find_element_by_xpath("..")
        levels = 1
        accept_button = None
        while element_to_search_from != webdriver_instance:
            print(f"Searching for the accept button {levels} levels up, from element {element_to_search_from.get_attribute('outerHTML')[:100]}")
            accept_button = _find_accept_button_recurse(element_to_search_from)
            if accept_button is not None:
                print("Found the accept button!")
                break
            levels += 1
            if levels > 10:
                print("Max accept button search levels exceeded")
                break
            element_to_search_from = element_to_search_from.find_element_by_xpath("..")
            if element_to_search_from.tag_name in ["html", "body"]:
                print("Reached top of document, aborting search")
                break

        if accept_button is None:
            print("Accept button not found, force hiding")
            # Try to hide the cookie popup forcefully
            __do_hide(webdriver_instance, cookie_text_element.find_element_by_xpath(".."))
            if element_was_visible and not target_element.is_displayed():
                print("Element was on the popup, aborting")
                activity.get(webdriver_instance)
                return False
            return True

        time.sleep(1)

        try:
            if element_was_visible and not target_element.is_displayed():
                print("Element was on the popup, aborting")
                activity.get(webdriver_instance)
                return False
            if cookie_text_element.is_displayed():
                # We clicked the wrong button!
                print("Wrong button clicked, reloading and force hiding")
                stored_element = element.Element(cookie_text_element, webdriver_instance)
                activity.get(webdriver_instance)
                __do_hide(webdriver_instance, stored_element.get_element(webdriver_instance).find_element_by_xpath(".."))
                return True
        except (StaleElementReferenceException, element.ElementLostException):
            # The cookie text element is gone, this is good
            pass

        if element_was_visible and not target_element.is_displayed():
            print("Element was on the popup, aborting")
            activity.get(webdriver_instance)
            return False

        print("Cookie popup hidden successfully")
        return True
    except (StaleElementReferenceException, element.ElementLostException):
        print("Element lost while hiding popup")
        return False


def __do_hide(webdriver_instance, element):
    webdriver_instance.execute_script("arguments[0].style.display = 'none';", element)
