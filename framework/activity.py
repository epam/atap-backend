import inspect
import json
import re
import time
from typing import Optional, List, Union

from retry import retry
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.common.exceptions import (
    NoSuchWindowException,
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    InvalidSessionIdException,
    TimeoutException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.exceptions import MaxRetryError

from framework.element import Element
from framework.libs.popup_detector import detect_popup, wait_for_popup
from framework.tools import authentication
from framework.await_page_load import wait_for_page_load


class IllegalArgumentError(ValueError):
    pass


class Activity:
    def __init__(self, name, url, options, page_after_login, commands, page_resolution=None):
        self.url = url
        self.name = name
        self.options = options
        self.page_after_login = page_after_login
        self.commands = commands
        self.windows_in_store = {}
        self.page_resolution = tuple(map(int, page_resolution.split("x"))) if page_resolution else None

    def ignore_command(self, number_of_command, current_command):
        command = current_command["command"]
        return (
            (command == "mouseOver" and self.commands[number_of_command + 1]["command"] == "mouseOut")
            or (command == "mouseOut" and self.commands[number_of_command - 1]["command"] == "mouseOver")
            or (command == "close" and number_of_command == len(self.commands) - 1)
            or (command == "open" and number_of_command == 0)
            or command == "setWindowSize"
        )

    def get(self, webdriver_instance: RemoteWebDriver, try_again: Optional[bool] = True):
        if not hasattr(webdriver_instance, "authenticated"):
            authentication.memorize_authentication(webdriver_instance, False)

        if self.page_resolution:
            webdriver_instance.set_window_size(*self.page_resolution)
        self.open(webdriver_instance, {})

        for i, command in enumerate(self.commands):
            if self.ignore_command(i, command):
                continue

            state = {"windows_in_store": {}}
            if "opensWindow" in command:
                args = (
                    webdriver_instance,
                    state,
                    command["target"],
                    command["targets"],
                    command["value"],
                    command["opensWindow"],
                    command["windowHandleName"],
                )
            else:
                args = (webdriver_instance, state, command["target"], command["targets"], command["value"])
            try:
                res = getattr(self, camel_case_to_snake_case(command["command"]))(*args)
            except AttributeError:
                raise IllegalArgumentError(f'Command {command["command"]} not found.')

            if res is not None:
                if try_again and res.startswith("Connection error"):
                    webdriver_instance.quit()
                    self.get(webdriver_instance, try_again=False)
                    return
                raise IllegalArgumentError(f"The command {command} is incorrect: {res}")
        wait_for_page_load(webdriver_instance)

    def open(self, driver, state, target="", targets=None, value=None):
        if not isinstance(driver, webdriver.Firefox):
            driver.limiter.delay_access(register=True, count=2)

        if not driver.authenticated and self.options is not None and self.options != "":
            try:
                auth_by_options(driver, self.options)
                authentication.memorize_authentication(driver, True)
            except Exception as e:
                print(f"Error in activity -> open -> auth_by_options: {e}")
                self.close_current_window(driver, {})

        if not self.page_after_login:
            driver.get(self.url)

    def close(self, driver, state, target, targets, value):
        self.close_current_window(driver, state)

    def switch_to_window_with_name(self, driver, state, target_name):
        # check every window to try to find the given window name
        original_handle = driver.current_window_handle
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            current_name = driver.execute_script("return window.name")
            if target_name == current_name:
                return
        driver.switch_to.window(original_handle)
        return f"Window with this name={target_name} was not found!"

    def close_all_windows_except_current(self, driver, state):
        original_handle = driver.current_window_handle
        for handle in driver.window_handles:
            if handle != original_handle:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(original_handle)

    def close_current_window(self, driver, state):
        if len(driver.window_handles) > 1:
            current_window = driver.current_window_handle
            state["windows_in_store"] = {
                key: val for key, val in self.windows_in_store.items() if val != current_window
            }
            driver.close()
        else:
            state["windows_in_store"] = {}
            driver.quit()

    def run_script(self, driver, state, target, targets, value):
        driver.execute_script(target)

    def handle_window_with_title(self, driver, state, title):
        original_handle = driver.current_window_handle
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            current_name = driver.execute_script("return window.name")
            if title == current_name:
                driver.switch_to.window(original_handle)
                time.sleep(1)
                return handle

    def store_window_handle(self, driver, state, target, targets, value: str) -> None:
        """

        :param target: str, title=... or tab=int or just str
        :param targets: List[List[str]]
        :param value: str
        :return:
        """
        if target.startswith("title"):
            state["windows_in_store"][value] = self.handle_window_with_title(driver, state, target[6:])
            return
        if target.startswith("tab"):
            state["windows_in_store"][value] = driver.window_handles[
                self.number_of_root_windows(driver) + int(target[4:])
            ]
            return
        self.windows_in_store[target] = driver.current_window_handle

    def open_page_in_new_window(self, driver, state, url):
        driver.execute_script("window.open()")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(url)

    def number_of_root_windows(self, driver):
        current_window = driver.current_window_handle
        driver.switch_to.default_content()
        idx = driver.window_handles.index(driver.current_window_handle)
        driver.switch_to.window(current_window)
        return idx

    def close_popup(self, driver, state, target, targets, value):
        detect_popup(driver)

    def wait_for_popup(self, driver, state, target, targets, value):
        wait_for_popup(driver)

    def select_window(self, driver, state, target, targets, value):
        """

        :param target: str, handle=${...} or tab=number(int)/close/open/closeallother or title=...
        :param targets: List[List[str]]
        :param value: str, if target=='tab=open', value is url
        :return:
        """
        if target.startswith("title"):
            try:
                driver.switch_to.window(target[6:])
            except NoSuchWindowException:
                self.switch_to_window_with_name(driver, state, target[6:])

        elif target.startswith("tab"):
            if target == "tab=close":
                self.close_current_window(driver, state)
                return
            if target == "tab=closeallother":
                self.close_all_windows_except_current(driver, state)
                return
            if target == "tab=open":
                self.open_page_in_new_window(driver, state, value)
                return
            driver.switch_to.window(driver.window_handles[self.number_of_root_windows(driver) + int(target[4:])])

        elif target.startswith("handle"):
            if target[target.find("{") + 1 : target.find("}")] in state["windows_in_store"]:
                driver.switch_to.window(state["windows_in_store"][target[target.find("{") + 1 : target.find("}")]])
            else:
                return f"The {target} has an incorrect format"

    def select_frame(self, driver: RemoteWebDriver, state, target, targets, value):
        """

        :param target: relative=top / relative=parent
                       index=0,1,2,3,...
        :param targets: List[List[str]]
        :param value: str

        :return:
        """
        if target.startswith("index"):
            driver.switch_to.frame(int(target[6:]))
            time.sleep(1)
        if target == "relative=top":
            driver.switch_to.default_content()
            time.sleep(1)
        if target == "relative=parent":
            driver.switch_to.parent_frame()
            time.sleep(1)

    def type(self, driver: RemoteWebDriver, state, target, targets, value):
        """

        :param target: str, "css=..." or "id=..." or "xpath=..." or "name=..."
        :param targets: List[List[str]]
        :param value: str
        :return:
        """
        element = self.get_element_from_target(driver, target, targets)
        if element is None:
            return "The element was not found on the page."
        self.try_send_keys(element.get_element(driver), value)
        time.sleep(1)

    def select(self, driver: RemoteWebDriver, state, target, targets, value):
        """

        :param target: str, "css=..." or "id=..." or "xpath=..." or "name=..."
        :param targets: List[List[str]]
        :param value: str, (label=, value=, id=, index=), label may be contains '*'
        :return:
        """
        element = self.get_element_from_target(driver, target, targets)
        if element is None:
            return "The element was not found on the page."
        else:
            element = element.get_element(driver)

        select = Select(element)
        if value.startswith("index"):
            select.select_by_index(value[6:])
            time.sleep(1)
        if value.startswith("value"):
            select.select_by_value(value[6:])
            time.sleep(1)
        if value.startswith("label") and value.find("*") == -1:
            select.select_by_visible_text(value[6:])
            time.sleep(1)
        elif value.startswith("label"):
            for option in select.options:
                if option.text.find(value[6:].replace("*", "")) != -1:
                    select.select_by_visible_text(option.text)
                    time.sleep(1)
                    break
            else:
                return f"Invalid value={value} format."
        if value.startswith("id"):
            for option in select.options:
                id_attr = option.get_attribute("id")
                if id_attr and id_attr == value[3:]:
                    select.select_by_visible_text(option.text)
                    time.sleep(1)
                    break
                else:
                    return f"Invalid value={value} format."

    def set_window_size(self, driver: RemoteWebDriver, state, target, targets, value):
        """

        :param target: str, (e.g. "", "1936x1056")
        :param targets: List[List[str]]
        :param value: str
        :return:
        """
        if not target:
            driver.maximize_window()
            time.sleep(1)
        else:
            try:
                target = [int(i) for i in target.split("x")]
            except ValueError:
                return "Invalid window size format."
            if len(target) == 2:
                driver.set_window_size(target[0], target[1])
                time.sleep(1)
            else:
                return "Invalid window size format."

    def scroll(self, driver: RemoteWebDriver, elem: WebElement):
        x, y = elem.location.values()
        height, width = elem.size.values()
        y1 = y + height
        driver.execute_script("window.scrollTo(0, 0)")
        total = driver.execute_script("return document.body.scrollHeight")
        viewport = driver.execute_script("return window.innerHeight")
        top = 0
        bot = viewport
        while not (top < y < bot and top < y1 < bot):
            top += viewport // 4
            bot += viewport // 4
            driver.execute_script(f"window.scrollTo(0, {top})")
            if top > total:
                return

    def scroll_to_coors(self, driver, x, y):
        scroll_by_coord = "window.scrollTo(%s,%s);" % (x, y)
        driver.execute_script(scroll_by_coord)

    def mouse_over(self, driver, state, target, targets, value):
        """

        :param target: str, "css=..." or "id=..." or "xpath=..." or "name=..."
        :param targets: List[List[str]]
        :param value: str
        :return:
        """
        element = self.get_element_from_target(driver, target, targets)
        if element is None:
            return "The element was not found on the page."

        element = element.get_element(driver)
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(4)
        self.try_send_keys(element, "")
        time.sleep(4)

    def mouse_out(self, driver, state, target, targets, value):
        """

        :param target: str, "css=..." or "id=..." or "xpath=..." or "name=..."
        :param targets: List[List[str]]
        :param value: str
        :return:
        """
        element = self.get_element_from_target(driver, target, targets)
        if element is None:
            return "The element was not found on the page."
        if is_visible(element, driver):
            element = element.get_element(driver)
            size = element.size
            location = element.location
            self.scroll_to_coors(
                driver, location["x"] + 2 * size["height"] + 10, location["y"] + size["width"] + 10
            )
            time.sleep(4)
            ActionChains(driver).move_to_element_with_offset(
                to_element=element, xoffset=size["height"] + 10, yoffset=size["width"] + 10
            ).perform()
            time.sleep(1)

    @retry((ElementNotInteractableException, StaleElementReferenceException), delay=1, tries=7, backoff=2)
    def try_send_keys(self, elem: WebElement, value):
        elem.send_keys(value)

    def send_keys(self, driver, state, target, targets, value):
        """

        :param target: str, "css=..." or "id=..." or "xpath=..." or "name=..."
        :param targets: List[List[str]]
        :param value: str, sequence of keys to type, can be used to send key strokes (e.g. '${KEY_ENTER}' or
        'o${KEY_CTRL}${KEY_LEFT}${KEY_CTRL}g')
        :return:
        """

        element = self.get_element_from_target(driver, target, targets)
        if element is None:
            return "The element was not found on the page."
        else:
            element = element.get_element(driver)
        keys_matching = None
        for v in value.replace("${", "}").split("}"):
            if v.startswith("KEY_"):
                if keys_matching is None:
                    attributes = inspect.getmembers(Keys, lambda a: not (inspect.isroutine(a)))
                    keys_matching = dict(
                        [a for a in attributes if not (a[0].startswith("__") and a[0].endswith("__"))]
                    )
                if v[4:] in keys_matching:
                    self.try_send_keys(element, keys_matching[v[4:]])
                    time.sleep(1)
                else:
                    return f"Key {v} not found."
            else:
                self.try_send_keys(element, v)
                time.sleep(1)

    @retry(
        (ElementNotInteractableException, ElementClickInterceptedException, StaleElementReferenceException),
        delay=1,
        tries=7,
        backoff=2,
    )
    def click_attempt(self, element: WebElement):
        element.click()

    def click(self, driver, state, target, targets, value, open_window=False, window_handle_name=None):
        element = self.get_element_from_target(driver, target, targets)
        if element is None:
            return "The element was not found on the page."
        element = element.get_element(driver)

        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(4)

        try:
            self.click_attempt(element)
            time.sleep(1)
        except (InvalidSessionIdException, MaxRetryError) as err:
            return f"Connection error: {err}"
        except (ElementNotInteractableException, ElementClickInterceptedException) as err:
            return str(err)

        if open_window and window_handle_name:
            state["windows_in_store"][window_handle_name] = driver.window_handles[
                self.number_of_root_windows(driver) + 1
            ]
            time.sleep(1)

    def try_to_get_elements(self, driver: RemoteWebDriver, target: str, by_matching):
        way = camel_case_to_snake_case(target[: target.find("=")]).upper()
        way = way + "_SELECTOR" if way == "CSS" else way

        try:
            return Element(
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((by_matching[way], target[target.find("=") + 1 :]))
                ),
                driver,
            )
        except (NoSuchElementException, TimeoutException):
            return None

    def get_element_from_target(
        self, driver: RemoteWebDriver, target: str, targets: List[List[str]]
    ) -> Optional[Element]:
        """
        :param target: str, "css=..." or "id=..." or "xpath=..." or "name=..."
        :param targets: List[List[str]], strings in list - "css=..." or "id=..." or "xpath=..." or "name=..."
        :return:
        """
        attributes = inspect.getmembers(By, lambda a: not (inspect.isroutine(a)))
        by_matching = dict([a for a in attributes if not (a[0].startswith("__") and a[0].endswith("__"))])
        targets = [target] + [i[0] for i in targets]
        for target in targets:
            elem = self.try_to_get_elements(driver, target, by_matching)
            if elem is not None:
                return elem


def is_visible(element: Union[Element, WebElement], driver: RemoteWebDriver) -> bool:
    element = element.get_element(driver) if isinstance(element, Element) else element
    return element and element.size["width"] * element.size["height"] > 0 and element.is_displayed()


def camel_case_to_snake_case(name: str) -> str:
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    return pattern.sub("_", name).lower()


def snake_case_to_camel(name: str) -> str:
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def auth_by_options(webdriver_instance: RemoteWebDriver, options: str) -> None:
    options = json.loads(options)
    if options["auth_required"]:
        if options["auth_type"] == "modal":
            authentication.auth_by_modal(webdriver_instance, options["auth_setting"])
        elif options["auth_type"] == "page":
            authentication.auth_by_page(webdriver_instance, options["auth_setting"])
        elif options["auth_type"] == "alert":
            authentication.auth_by_alert(webdriver_instance, options["auth_setting"])

    wait_for_page_load(webdriver_instance)


def load_activities(page_info: dict, webdriver_instance: RemoteWebDriver) -> List[Activity]:
    activities = []
    url = page_info["url"]
    options = page_info["options"]

    auth_by_options(webdriver_instance, options)
    # if not page_info["page_after_login"]:
    #     webdriver_instance.limiter.delay_access(register=True, count=1)
    #     webdriver_instance.get(url)
    # time.sleep(1)

    if "activities" in page_info and len(page_info["activities"]) > 0:
        for activity_info in page_info["activities"]:
            page_resolution = page_info["page_resolution"]
            name = activity_info["name"]
            element_locators = (
                list(filter(lambda x: x, activity_info["element_click_order"]))
                if activity_info["element_click_order"] is not None
                else None
            )
            if activity_info["side_file"]:
                for test in eval(
                    str(activity_info["side_file"]).replace("true", "True").replace("false", "False")
                )["tests"]:
                    activities.append(
                        Activity(
                            name=name,
                            url=url,
                            options=options,
                            commands=test["commands"],
                            page_after_login=page_info["page_after_login"],
                            page_resolution=page_info["page_resolution"],
                        )
                    )
            else:
                commands = []
                for element_locator in element_locators:
                    commands.append(
                        {"command": "click", "target": f"css={element_locator}", "targets": [], "value": ""}
                    )
                activities.append(
                    Activity(
                        name=name,
                        url=url,
                        options=options,
                        commands=commands,
                        page_after_login=page_info["page_after_login"],
                        page_resolution=page_info["page_resolution"],
                    )
                )

    else:
        activities.append(
            Activity(
                name="Main Activity",
                url=url,
                options=options,
                page_after_login=page_info["page_after_login"],
                commands=[],
                page_resolution=page_info["page_resolution"],
            )
        )
    return activities
