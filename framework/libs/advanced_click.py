import time
from framework.element import ElementLostException, JS_PATCH, DELAY_AFTER_GET
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException, ElementNotInteractableException,\
    ElementClickInterceptedException, InvalidSessionIdException, TimeoutException, StaleElementReferenceException


def advanced_link_click(element, webdriver_instance: webdriver.Firefox):
        webdriver_instance.limiter.delay_access(register=False)
        prev_url = webdriver_instance.current_url
        body = webdriver_instance.find_element_by_css_selector('body')
        try:
            result = {
                "action": "NONE"
            }
            webdriver_instance.execute_script(JS_PATCH)
            element.get_element(webdriver_instance).click()
            # TODO: Fix for firefox
            time.sleep(DELAY_AFTER_GET)
            if element._dismiss_alert(webdriver_instance):
                result = {
                    "action": "ALERT"
                }
            tab_url = element._check_if_new_tab_opened(webdriver_instance)
            if tab_url is not None:
                result = {
                    "action": "NEWTAB",
                    "url": tab_url
                }
            if webdriver_instance.current_url != prev_url:

                if not element.is_same_page(webdriver_instance.current_url, prev_url):
                    try:
                        body.send_keys(Keys.NULL)
                        result = {
                            "action": "INTERNALLINK",
                            "url": webdriver_instance.current_url
                        }
                    except StaleElementReferenceException:
                        result = {
                            "action": "PAGECHANGE",
                            "url": webdriver_instance.current_url
                        }

                    if not element.is_same_site(webdriver_instance.current_url, prev_url) and result["action"] != "INTERNALLINK":
                        webdriver_instance.limiter.register_request()
                    webdriver_instance.get(prev_url)
                    time.sleep(DELAY_AFTER_GET)
            return result
        except (ElementNotInteractableException, ElementClickInterceptedException):
            return {
                "action": "NONINTERACTABLE"
            }
        except (NoSuchElementException, ElementLostException, StaleElementReferenceException):
            return {
                "action": "LOSTELEMENTEXCEPTION"
            }