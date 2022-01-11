from selenium import webdriver
import time
from .hide_cookie_popup import _find_accept_button_recurse
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException, StaleElementReferenceException, MoveTargetOutOfBoundsException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import random
import numpy as np
import scipy.interpolate as si

SCROLL_ITERATIONS = 3
SUBSCROLL_ITERATIONS = 10


def __get_highest_z_index(webdriver_instance):
    print("Retrieving elements...")
    all_elements = webdriver_instance.find_element_by_tag_name("html").find_elements_by_xpath(".//*")
    print(f"There are {len(all_elements)} elements on the page")

    max_z_index = -99999999999
    max_z_element = None
    indices = list()
    for element_id, element in enumerate(all_elements):
        print(f"\rChecking for the highest z-index...{element_id}/{len(all_elements)}", end="")
        if not element.is_displayed():
            continue
        z_index = element.value_of_css_property("z-index")
        if z_index != "auto":
            try:
                z_index = int(z_index)
                if z_index > max_z_index:
                    max_z_index = z_index
                    max_z_element = element
            except ValueError:
                continue

    print()
    print(f"The max z-index is {max_z_index}")

    return max_z_element, max_z_index


def wait_for_popup(webdriver_instance):
    for iteration in range(SCROLL_ITERATIONS):
        scroll_height = webdriver_instance.execute_script("return document.body.scrollHeight")

        elements_to_hover = list()
        elements_to_hover.extend(webdriver_instance.find_elements_by_tag_name("a"))
        elements_to_hover.extend(webdriver_instance.find_elements_by_tag_name("button"))

        dimensions = webdriver_instance.get_window_size(webdriver_instance.current_window_handle)
        for i in range(SUBSCROLL_ITERATIONS):
            print(
                f"\rScrolling back and forth and waiting for the popup, iteration {iteration+1}/{SCROLL_ITERATIONS} {int(i / SUBSCROLL_ITERATIONS * 50)}%", end="")
            time.sleep(1)
            target_scroll = int(scroll_height/SUBSCROLL_ITERATIONS*i)
            webdriver_instance.execute_script("window.scrollTo(0, arguments[0]);", target_scroll)
            for i in range(10):
                try:
                    ac = ActionChains(webdriver_instance)
                    ac.move_to_element(random.choice(elements_to_hover)).perform()
                except (MoveTargetOutOfBoundsException, WebDriverException):
                    pass

        for i in range(SUBSCROLL_ITERATIONS):
            print(
                f"\rScrolling back and forth and waiting for the popup, iteration {iteration+1}/{SCROLL_ITERATIONS} {50 + int(i / SUBSCROLL_ITERATIONS * 50)}%", end="")
            time.sleep(1)
            target_scroll = int(scroll_height/SUBSCROLL_ITERATIONS*(SUBSCROLL_ITERATIONS-i))
            webdriver_instance.execute_script("window.scrollTo(0, arguments[0]);", target_scroll)
            for _ in range(10):
                try:
                    ac = ActionChains(webdriver_instance)
                    ac.move_to_element(random.choice(elements_to_hover)).perform()
                except (MoveTargetOutOfBoundsException, WebDriverException):
                    pass

    print()


def detect_popup(webdriver_instance: webdriver.Firefox):
    wait_for_popup(webdriver_instance)
    max_z_element, max_z_index = __get_highest_z_index(webdriver_instance)
    if max_z_element is None:
        print("No element is on top of all others, cannot detect a popup")
        return
    print()
    print("========POPUP SRC========")
    print(max_z_element.get_attribute("outerHTML"))
    print("Popup acquired, searching for the close button")
    close_button = _find_accept_button_recurse(max_z_element, max_depth=20)
    print()
    if close_button is not None:
        print("========CLOSE BUTTON SRC========")
        try:
            print(close_button.get_attribute("outerHTML"))
        except StaleElementReferenceException:
            print("StaleElementReference, source is unavailable")
    else:
        print("Could not find the close button, attempting to force-hide the popup")
        webdriver_instance.execute_script("arguments[0].setAttribute('style','visibility:hidden;');", max_z_element)
