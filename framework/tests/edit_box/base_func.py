from selenium.common.exceptions import ElementNotInteractableException, InvalidElementStateException
from selenium.webdriver.remote.webelement import WebElement

from framework.element import Element
from framework.element_wrapper import ElementWrapper

EDIT_BOXES = {
    "editbox",
    "edit-box",
    "edit box",
    "edit_box",
    "boxedit",
    "box_edit",
    "box-edit",
    "box edit",
}

FAKE_TEXT = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."


class BaseFunc:
    def __init__(self, webdriver, text=None):
        self._dr = webdriver
        self._wrapper = ElementWrapper

    def _wrap(self, el):
        return self._wrapper(el, self._dr)

    def send_text(self, el, text=FAKE_TEXT):
        """
        Method for testing inserting text in edit box or his children
        """
        try:
            self._wrap(el).element.send_keys(text)
            return True
        except ElementNotInteractableException:
            return any(self.send_text(el) for el in el.find_by_xpath("./*", self._dr))
        except InvalidElementStateException:
            return False

    def is_btn(self, el):
        """
        A method that verifies that an item is a button
        """
        btn = self.contains_keywords(el, ["button"])
        input_el = el.tag_name == "input" or \
            self._wrap(el)["type"] in ["button", "submit"]

        return any([btn, input_el])

    @staticmethod
    def contains_keywords(el, words=None):
        """
        Search edit box by keywords in source
        """
        if words is None:
            words = EDIT_BOXES
        return any(word for word in words if word in el.source)
