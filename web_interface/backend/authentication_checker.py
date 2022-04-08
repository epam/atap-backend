import json
import logging

from dataclasses import dataclass

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSelectorException,
    NoSuchElementException,
)
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver, WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from web_interface.backend.url_checker import check_url
from web_interface.backend.auth_network_requests import auth_proceed
from framework import await_page_load
from framework.tools.authentication import auth_by_page, auth_by_modal, auth_by_alert

logger = logging.getLogger("authentication_checker")


def authentication_result(
    verified_auth_output,
):
    result = CheckAuthenticationResponse(message="Success", is_valid=True)

    if verified_auth_output == "Fast Delay Interim":
        result = CheckAuthenticationResponse(
            message="Webpage stuck on sending credentials. Tried waiting 25s for the response.", is_valid=False
        )
    if not verified_auth_output:
        result = CheckAuthenticationResponse(
            message="It seems that log in was unsuccessful. Please check user credentials.", is_valid=False
        )

    return result


@auth_proceed
def verify_auth_by_page(driver, auth_options, modal=False, **kwargs):
    return auth_by_page(driver, auth_options, modal=False)


@auth_proceed
def verify_auth_by_modal(driver, auth_options, **kwargs):
    return auth_by_modal(driver, auth_options)


@auth_proceed
def verify_auth_by_alert(driver, auth_options, **kwargs):
    return auth_by_alert(driver, auth_options)


@dataclass
class CheckAuthenticationResponse:
    message: str
    is_valid: float


class AuthenticationChecker:
    def __init__(self, url, auth_type, auth_setting):
        self.url = url
        self.type = auth_type
        self.options = auth_setting if isinstance(auth_setting, dict) else json.loads(auth_setting)
        self.dr: RemoteWebDriver = None

    def execute(self) -> CheckAuthenticationResponse:
        logger.info("Checking authentication for %s", self.type)
        result = None
        if self.type == "modal":
            result = self.__execute_for_modal()
        elif self.type == "page":
            result = self.__execute_for_page()
        elif self.type == "alert":
            result = self.__execute_for_alert()
        self.__close()
        return result

    def __verify_auth(self, auth_by_type, auth_options, listening_lag_ms=1000, modal=False):
        url = self.dr.current_url

        # * uses new driver, different from framework's
        login_res = auth_by_type(self.dr, auth_options, modal=modal, url=url, listening_lag_ms=listening_lag_ms)

        while login_res == "Fast Delay Interim" and listening_lag_ms <= 25000:
            listening_lag_ms *= 5
            login_res = auth_by_type(
                self.dr, auth_options, modal=modal, url=url, listening_lag_ms=listening_lag_ms
            )

        if login_res == "Fast Delay Interim":
            login_res = False

        return login_res

    def __open_page(self, url: str):
        self.dr = webdriver.Firefox()
        self.dr.set_page_load_timeout(20)
        try:
            self.dr.get(url)
        except TimeoutException:
            logger.warning("Get timed out, processing with partially loaded site")
        logger.info("Waiting for the page to load")
        await_page_load.wait_for_page_load(self.dr)

        return True

    def __find_element(self, css_selector: str):
        try:
            return self.dr.find_element_by_css_selector(css_selector)
        except (InvalidSelectorException, NoSuchElementException):
            return None

    def __close(self):
        if self.dr is not None:
            self.dr.quit()

    def __execute_for_page(self) -> CheckAuthenticationResponse:
        check_url_response = check_url(self.options["activator"])

        if not check_url_response.is_valid:
            return CheckAuthenticationResponse(message=check_url_response.message, is_valid=False)

        if not self.__open_page(self.options["activator"]):
            return CheckAuthenticationResponse(
                message=f'The page {self.options["activator"]} could not be opened.', is_valid=False
            )

        auth_passed = self.__verify_auth(verify_auth_by_page, self.options)

        return authentication_result(auth_passed)

    def __execute_for_modal(self) -> CheckAuthenticationResponse:
        if not self.__open_page(self.url):
            return CheckAuthenticationResponse(message=f"The page {self.url} could not be opened.", is_valid=False)

        button = self.__find_element(self.options["activator"])

        if button is None:
            return CheckAuthenticationResponse(
                message=f'The element with the css selector "{self.options["activator"]}" is not on the page {self.url}.',
                is_valid=False,
            )

        if not button.is_displayed() or not button.is_enabled():
            return CheckAuthenticationResponse(
                message=f'The element with the css selector "{self.options["activator"]}" can not be accessed.',
                is_valid=False,
            )

        auth_passed = self.__verify_auth(verify_auth_by_modal, self.options, modal=True)

        return authentication_result(auth_passed)

    def __execute_for_alert(self) -> CheckAuthenticationResponse:
        if not self.__open_page(self.url):
            return CheckAuthenticationResponse(message=f"The page {self.url} could not be opened.", is_valid=False)

        auth_passed = self.__verify_auth(verify_auth_by_alert, self.options)

        return authentication_result(auth_passed)
