import time
from typing import Optional, Iterable, Callable, Any, List
from urllib.parse import urlparse

from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.common.exceptions import (
    StaleElementReferenceException, ElementClickInterceptedException,
    ElementNotInteractableException, NoAlertPresentException, NoSuchElementException
)
from selenium.webdriver.remote.webelement import WebElement


class ElementLostException(Exception):
    """Element could no longer be found on the page"""
    pass


DELAY_AFTER_GET = 0.5


JS_PATCH = (
    '''
    let btn_print = arguments[0];
    window.print=function(){console.warn("Print button")};
    Window.prototype.print=window.print;
    oldOpen=window.open;
    window.open=function(){var w = oldOpen(...arguments);w.print=window.print;return w};
    '''
)

JS_GET_ATTRS = (
    '''
    var items = {};
    for (index = 0; index < arguments[0].attributes.length; ++index) {
        items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value
    };
    return items;
    '''
)

JS_BUILD_CSS_SELECTOR = (
    '''
    var element = arguments[0];
    var useID = arguments[1];
    var path = [];
    while (element.nodeType === Node.ELEMENT_NODE) {
        var selector = element.nodeName.toLowerCase();
            if (element.id && useID) {
                selector += '#' + element.id;
                path.unshift(selector);
                break;
            } else {
                var sib = element, nth = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.nodeName.toLowerCase() == selector)
                       nth++;
                }
                if (nth != 1)
                    selector += ":nth-of-type("+nth+")";
            }
            path.unshift(selector);
            element = element.parentNode;
    }
    return path.join(" > ");
    '''
)


class Element:
    def __init__(self,
                 element: Optional[WebElement],
                 webdriver_instance: RemoteWebDriver,
                 selector: Optional[str] = None,
                 selector_no_id: Optional[str] = None,
                 force_rebuild_selector: bool = False):

        if selector_no_id is not None:
            # self.selector = selector
            self.selector = None
            self.selector_no_id = selector_no_id
            if webdriver_instance is not None:
                element = self._locate(webdriver_instance)

            if force_rebuild_selector:
                self._rebuild_selector(webdriver_instance, element)
        else:
            self._rebuild_selector(webdriver_instance, element)

        self.element = {}

        if element is not None:
            element_id = element.get_attribute('id')
            self.element_id = element_id if element_id != '' else None
            self.tag_name = element.tag_name
            self.source = element.get_attribute('outerHTML')
            self.position = element.location

        self.cached_attrs = None

    def _rebuild_selector(self, webdriver_instance, element):
        # self.selector = webdriver_instance.execute_script(JS_BUILD_CSS_SELECTOR, element, True)
        self.selector = None
        self.selector_no_id = webdriver_instance.execute_script(JS_BUILD_CSS_SELECTOR, element, False)

    def get_selector(self):
        if self.selector is not None:
            return self.selector
        else:
            return self.selector_no_id

    def __deepcopy__(self, memo) -> 'Element':
        element_copy = Element(None, None, self.selector, self.selector_no_id)
        element_copy.element_id = self.element_id
        element_copy.tag_name = self.tag_name
        element_copy.source = self.source
        return element_copy

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Element):
            return NotImplemented
        try:
            equal = any((
                    # self.selector is not None and self.selector == other.selector,
                    self.selector_no_id == other.selector_no_id,
                    self.source == other.source and self.position == other.position
            ))
        except AttributeError as _:
            equal = False
        return equal

    def __hash__(self) -> int:
        return hash(self.selector_no_id)

    def __repr__(self) -> str:
        return f'<Element: <{self.tag_name}>, Selector: "{self.selector_no_id}">'

    def safe_operation_wrapper(self, operation, on_lost: Optional[Callable] = None, *args, **kwargs):
        try:
            return operation(self, *args, **kwargs)
        except (StaleElementReferenceException, NoSuchElementException, ElementLostException):
            if on_lost is None:
                raise ElementLostException(f'Lost {self.selector_no_id} while safe-calling {operation.__name__}')
            else:
                return on_lost()

    def get_attributes(self, webdriver_instance: RemoteWebDriver, force: Optional[bool] = False) -> dict:
        if self.cached_attrs is None or force:
            def get_attrs(element):
                return webdriver_instance.execute_script(JS_GET_ATTRS, element.get_element(webdriver_instance))
            self.cached_attrs = self.safe_operation_wrapper(get_attrs)
        return self.cached_attrs

    def get_attribute(
            self, webdriver_instance: RemoteWebDriver, name: str, force: Optional[bool] = False
    ) -> Optional[str]:
        try:
            return self.get_attributes(webdriver_instance, force)[name]
        except KeyError:
            return None

    def get_parent(self, webdriver_instance: RemoteWebDriver) -> Optional['Element']:
        elements = self.find_by_xpath('./parent::*', webdriver_instance)
        if not elements:
            return None
        return elements[0]

    def get_text(self, webdriver_instance: RemoteWebDriver) -> str:
        try:
            return self.get_element(webdriver_instance).text
        except (StaleElementReferenceException, NoSuchElementException):
            raise ElementLostException(f'Lost {self.selector_no_id} while getting text')

    def _locate(self, webdriver_instance: RemoteWebDriver) -> Optional[WebElement]:
        if self.selector is not None:
            try:
                return webdriver_instance.find_element_by_css_selector(self.selector)
            except NoSuchElementException:
                self.selector = None
        if self.selector is None and self.selector_no_id is not None:
            try:
                return webdriver_instance.find_element_by_css_selector(self.selector_no_id)
            except NoSuchElementException:
                raise ElementLostException(
                    f'Could not locate an element {self.selector_no_id} on {webdriver_instance.current_url}'
                )
        return None

    def get_element(self, webdriver_instance: RemoteWebDriver) -> WebElement:
        try:
            # Dummy operation that raises an exception if the element needs to be found again
            if id(webdriver_instance) not in self.element:
                raise StaleElementReferenceException
            element = self.element[id(webdriver_instance)]
            _ = element.tag_name
            return element
        except (StaleElementReferenceException, NoSuchElementException):
            element = self._locate(webdriver_instance)
        self.element[id(webdriver_instance)] = element
        return element

    def click(self, webdriver_instance: RemoteWebDriver) -> dict:
        webdriver_instance.limiter.delay_access(register=False)
        prev_url = webdriver_instance.current_url
        try:
            result = {
                'action': 'NONE'
            }
            webdriver_instance.execute_script(JS_PATCH)
            self.get_element(webdriver_instance).click()
            time.sleep(DELAY_AFTER_GET)
            if self._dismiss_alert(webdriver_instance):
                result = {
                    'action': 'ALERT'
                }
            tab_url = self._check_if_new_tab_opened(webdriver_instance)
            if tab_url is not None:
                result = {
                    'action': 'NEWTAB',
                    'url': tab_url
                }
            if webdriver_instance.current_url != prev_url:
                if not self.is_same_page(webdriver_instance.current_url, prev_url):
                    if not self.is_same_site(webdriver_instance.current_url, prev_url):
                        webdriver_instance.limiter.register_request()
                    result = {
                        'action': 'PAGECHANGE',
                        'url': webdriver_instance.current_url
                    }
                    webdriver_instance.get(prev_url)
                    time.sleep(DELAY_AFTER_GET)
            return result
        except (ElementNotInteractableException, ElementClickInterceptedException):
            return {
                'action': 'NONINTERACTABLE'
            }
        except (NoSuchElementException, ElementLostException, StaleElementReferenceException):
            return {
                'action': 'LOSTELEMENTEXCEPTION'
            }

    @staticmethod
    def _dismiss_alert(webdriver_instance: RemoteWebDriver) -> bool:
        try:
            webdriver_instance.switch_to.alert.dismiss()
            return True
        except NoAlertPresentException:
            pass
        return False

    @staticmethod
    def _check_if_new_tab_opened(webdriver_instance: RemoteWebDriver) -> Optional[str]:
        if len(webdriver_instance.window_handles) > 1:
            webdriver_instance.switch_to.window(webdriver_instance.window_handles[1])
            tab_url = webdriver_instance.current_url
            webdriver_instance.close()
            webdriver_instance.switch_to.window(webdriver_instance.window_handles[0])
            return tab_url
        return None

    @staticmethod
    def is_same_page(url1: str, url2: str) -> bool:
        url1 = urlparse(url1)
        url2 = urlparse(url2)
        return url1.scheme == url2.scheme and url1.netloc == url2.netloc and url1.path == url2.path

    @staticmethod
    def is_same_site(url1: str, url2: str) -> bool:
        url1 = urlparse(url1)
        url2 = urlparse(url2)
        return url1.scheme == url2.scheme and url1.netloc == url2.netloc

    @staticmethod
    def safe_foreach(elements: list, callback: Callable) -> None:
        for element_id in reversed(range(len(elements))):
            try:
                callback(elements[element_id])
            except (StaleElementReferenceException, ElementLostException, NoSuchElementException):
                del elements[element_id]

    @staticmethod
    def from_webelement_list(webelements: Iterable[WebElement], webdriver_instance: RemoteWebDriver) -> List['Element']:
        elements = []
        for web_element in webelements:
            try:
                elements.append(Element(web_element, webdriver_instance))
            except (StaleElementReferenceException, NoSuchElementException):
                pass
        return elements

    def find_by_xpath(self, xpath: str, webdriver_instance: RemoteWebDriver) -> List['Element']:
        try:
            elements = self.get_element(webdriver_instance).find_elements_by_xpath(xpath)
        except (StaleElementReferenceException, NoSuchElementException):
            raise ElementLostException(f'Lost {self.selector_no_id} while searching by xpath')
        return self.from_webelement_list(elements, webdriver_instance)

    def is_displayed(self, webdriver_instance: RemoteWebDriver) -> bool:
        return self.get_element(webdriver_instance).is_displayed()
