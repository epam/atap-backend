import json
from re import search

from framework.tools.login_helper_script import autologin_tool_script, login_info_js
from framework import await_page_load
from selenium.common.exceptions import (
    NoSuchElementException,
    NoAlertPresentException,
    TimeoutException,
    StaleElementReferenceException,
    InvalidElementStateException,
    ElementClickInterceptedException,
    JavascriptException,
    WebDriverException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


email_regex = "^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$"
phone_regex = "^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$"


def _get_login_type(login_credential):
    return (
        search(email_regex, login_credential)
        and "email"
        or search(phone_regex, login_credential)
        and "tel"
        or "text"
    )


def _get_login_info(driver, input_type):
    driver.execute_script(autologin_tool_script)

    return driver.execute_script(
        login_info_js,
        input_type,
    )


def _extract_login_info(info):
    return (
        info.get("login"),
        info.get("submit"),
        info.get("password"),
    )


def _bring_to_view(driver, element):
    driver.execute_script("window.scrollBy(0, 0);")
    driver.execute_script(
        "window.scrollBy(0, arguments[0].getBoundingClientRect().y - window.innerHeight / 2);", element
    )


def _click_all_js(driver, element):
    driver.execute_script(
        """
            for (let elem of [arguments[0], ...arguments[0].getElementsByTagName("*")]) {
                elem.click();
            }
        """,
        element,
    )


def _button_click(driver, element):
    # * sometimes can't click with one of ways
    try:
        _bring_to_view(driver, element)
        element.click()  # * one way
    except (StaleElementReferenceException, ElementClickInterceptedException):
        pass
    try:
        _click_all_js(driver, element)
        # * other way
    except (StaleElementReferenceException, JavascriptException):
        pass


def send_auth(info, auth_data, no_password=True):
    login, password = auth_data.get("login"), auth_data.get("password")
    login_fields, login_buttons, password_fields = info

    if not login_fields and not password_fields:
        raise NameError("No login fields found. Not a login page.")

    try:
        if no_password:
            # * set login value for all fields are supposed to be 'login'
            [_input.send_keys(login) for _input in login_fields]
            # * submit without password to get it if hidden
        else:
            # clear login fields first
            [_input.send_keys("") for _input in login_fields]  # clear
            [_input.send_keys(login) for _input in login_fields]
            [_input.send_keys(password) for _input in password_fields]

        if not login_buttons:
            login_fields[0].send_keys(Keys.ENTER)
    except (InvalidElementStateException, StaleElementReferenceException):
        pass

    for btn in login_buttons:
        _button_click(send_auth.driver, btn)


def click_modal_activator(driver, selector):
    # * modal button activator
    button = driver.find_element_by_css_selector(selector)
    _button_click(driver, button)


def _proceed_to_login_page(driver, url):
    # print("_proceed_to_login_page")
    driver.set_page_load_timeout(20)

    # try:
    driver.get(url)  # * login page url activator
    await_page_load.wait_for_page_load(driver)


def memorize_authentication(webdriver_instance, auth_state):
    webdriver_instance.authenticated = auth_state


def auth_by_page(driver, auth_options, modal=False):
    auth_options = json.loads(auth_options)
    send_auth.driver = driver

    if modal:
        click_modal_activator(driver, auth_options["activator"])
    else:
        _proceed_to_login_page(driver, auth_options["activator"])

    await_page_load.wait_for_page_load(driver)

    login_type = _get_login_type(auth_options.get("login"))

    login_info = _get_login_info(driver, login_type)
    auth_info = _extract_login_info(login_info)
    _, login_buttons, password_fields = auth_info

    no_password = not password_fields
    send_auth(auth_info, auth_options, no_password=no_password)
    await_page_load.wait_for_page_load(driver)

    if not password_fields:
        login_info = _get_login_info(driver, login_type)

        # * submit again with login and password
        auth_info = _extract_login_info(login_info)
        send_auth(auth_info, auth_options, no_password=False)
        await_page_load.wait_for_page_load(driver)


def auth_by_modal(driver, auth_options):
    auth_by_page(driver, auth_options, modal=True)


def _safe_http_alert_form(auth_func):
    def try_direct_auth(driver, options):
        options = json.loads(options)
        try:
            auth_func(driver, options)
            driver.get(driver.current_url)
            driver.find_element_by_tag_name("body")  # * do anything
        except WebDriverException as webdriver_e:
            if webdriver_e.msg not in [
                "User prompt of type promptUserAndPass is not supported",
                "Dismissed user prompt dialog: This site is asking you to sign in.",
            ]:
                raise webdriver_e

            schema, rest_url = driver.current_url.split("://")
            direct_register_link = f"{schema}://{options['login']}:{options['password']}@{rest_url}"
            driver.get(direct_register_link)

            driver.find_element_by_tag_name("body")  # * do anything

    return try_direct_auth


@_safe_http_alert_form
def auth_by_alert(driver, auth_options: str):
    # * handle string to iterator for recursive alerts
    auth_options = type(auth_options).__name__ == "dict_keyiterator" and auth_options or iter(auth_options)

    try:
        WebDriverWait(driver, timeout=2).until(expected_conditions.alert_is_present())
        prompt = driver.switch_to.alert
        prompt.send_keys(next(auth_options))
        prompt.accept()

        if WebDriverWait(driver, timeout=2).until(expected_conditions.alert_is_present()):
            auth_by_alert(driver, auth_options)
    except StopIteration:
        pass
    except (TimeoutException, NoAlertPresentException):
        # * No login prompt or need to log in via link
        raise WebDriverException("Dismissed user prompt dialog: This site is asking you to sign in.")
