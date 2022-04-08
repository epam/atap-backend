import re
from time import time, sleep

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, JavascriptException, UnexpectedAlertPresentException
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from framework.tools.page_visible_count_script import (
    visual_discloser_tool_script,
    amount_of_loaded_visual_elements_of_any_size,
)

URL_REGEX = re.compile(
    r"^(?:http|ftp)s?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


JS_GET_PERFORMANCE_URL_CODES = """
    var performance =
        window.performance ||
        window.mozPerformance ||
        window.msPerformance ||
        window.webkitPerformance ||
        {};

    return (
        performance
            .getEntries()
            .map((nav) => Object({ url: nav.name, code: nav.responseEnd })) || []
    );
"""

MAX_BODY_LOAD_TRIES = 3
MAX_TRIES_BETWEEN_REQUESTS = 3
TIMEOUT = 30


class BodyLoadException(TimeoutException):
    def __init__(self, loading_timeout):
        self.message = f"Failed to load page body in {loading_timeout}s"
        super().__init__(self.message)


class PageBodyLoadedContent:
    def __init__(self):
        self.locator = (By.TAG_NAME, "body")
        self.threshold_elements_to_be_loaded = 25
        self.guaranteed_elements_threshold = 500

    def __call__(self, driver):
        body_element = driver.find_element(*self.locator)

        driver.execute_script(visual_discloser_tool_script)
        try:
            return (
                driver.execute_script(
                    """
                    return document.body.getElementsByTagName("*").length > arguments[0];
                """,
                    self.guaranteed_elements_threshold,
                )
                or (
                    driver.execute_script(amount_of_loaded_visual_elements_of_any_size, body_element)
                    > self.threshold_elements_to_be_loaded
                )
            )
        except JavascriptException:
            # * most likely too much recursion, so enough elements loaded
            return True


def wait_for_page_load(webdriver_instance: webdriver.Firefox) -> None:
    network_requests_exception, body_missing_exc = None, None
    request_observing_interval = 0.2
    body_wait_timeout = 0.5

    start = time()
    page_loading_time = 0

    try:
        # * set interval for page loading fast or slowly
        body_missing_exc = _verify_body_loaded(webdriver_instance, body_wait_timeout)
    except UnexpectedAlertPresentException:
        print("Alert present, not waiting for body to load")
        page_loading_time = time() - start
    else:
        if body_missing_exc:
            # * body still can appear as loading page, 0.1 to change
            body_wait_timeout, request_observing_interval = 0.1, 1

        (
            page_loading_time,
            body_missing_exc,
            network_requests_exception,
        ) = _do_network_until_body_loaded_before_timeout_reached(
            start,
            page_loading_time,
            body_missing_exc,
            body_wait_timeout,
            webdriver_instance,
            request_observing_interval,
        )

    if page_loading_time > TIMEOUT:
        _response_failed_to_load(body_missing_exc, network_requests_exception)
        _response_failed_to_load(body_missing_exc, network_requests_exception)
        if webdriver_instance.current_url != "about:blank":
            print(f"Page {webdriver_instance.current_url} unreachable")
        else:
            print("Page unreachable and didn't response")
        print("Continue anyway")
    else:
        print(f"Page loaded, delayed {page_loading_time:.3f}s")


def _verify_body_loaded(webdriver_instance, timeout):
    try:
        body_loaded = presence_of_element_located((By.TAG_NAME, "body"))
        WebDriverWait(webdriver_instance, timeout).until(body_loaded)

        body_content_loaded = PageBodyLoadedContent()
        WebDriverWait(webdriver_instance, timeout).until(body_content_loaded)
    except TimeoutException:
        return BodyLoadException(timeout)

    return None


def _response_failed_to_load(locate_exc, network_exc):
    if locate_exc:
        print(f"Location exception occurred {locate_exc}")
    if network_exc:
        print(f"Last network exception occurred {network_exc}")


def _do_network_until_body_loaded_before_timeout_reached(
    page_get_timestamp, elapsed, body_exc, locate_timeout, *args
) -> (float, Exception, Exception):
    urls = []
    load_exception = None
    load_tries = 0

    while not elapsed or elapsed < TIMEOUT and (body_exc and load_tries < MAX_BODY_LOAD_TRIES):
        load_tries += 1
        load_exception = _collect_network_requests_while_requests_refreshing(*args, urls, load_exception)

        # * check body finally present after network stop, args[0] is webdriver instance
        body_exc = _verify_body_loaded(args[0], locate_timeout)
        elapsed = time() - page_get_timestamp

    if load_tries == MAX_BODY_LOAD_TRIES:
        print("It appears webpage has less than 25 visible elements. Body loaded")
        body_exc = None

    return elapsed, body_exc, load_exception


def _collect_network_requests_while_requests_refreshing(*args) -> Exception:
    network_frames = []
    tries_without_requests = 0
    webdriver_instance, request_observing_interval, urls, load_exception = args

    while tries_without_requests < MAX_TRIES_BETWEEN_REQUESTS:
        try:
            network_frames = webdriver_instance.execute_script(JS_GET_PERFORMANCE_URL_CODES) or []
        except JavascriptException as exc:
            load_exception = exc
            print(f"JavascriptException {load_exception}")
            sleep(request_observing_interval)
            continue
        except UnexpectedAlertPresentException:
            print("Alert present, not waiting any longer")
            return
        except Exception as exc:
            load_exception = exc
            sleep(request_observing_interval)
            print(f"Uncommon exception occurred: {load_exception}")
            continue

        urls, tries_without_requests = _update_responses(
            network_frames, urls, request_observing_interval, tries_without_requests
        )

    return load_exception


def _update_responses(responses, collected_responses, interval, unaltered_tries) -> (list, int):
    waiting_count = 0

    # * execute_script returns None insurance
    # * usually not reproducible
    if responses is None:
        unaltered_tries = 0
        return collected_responses, unaltered_tries

    unaltered_tries += 1
    for resp in responses:
        resp_url, resp_code = resp["url"], resp.get("code")
        if URL_REGEX.match(resp_url) is None:
            continue
        if resp_url not in collected_responses:
            unaltered_tries = 0
            if resp_code is not None:
                collected_responses.append(resp_url)
            else:
                waiting_count += 1
    if waiting_count:
        print(f"Still waiting for {waiting_count} requests")
    sleep(interval)

    return collected_responses, unaltered_tries
