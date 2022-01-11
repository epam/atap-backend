import abc
from selenium import webdriver


class Test(metaclass=abc.ABCMeta):
    """
    Interface which determines the behavior of the heirs.
    .. note::
        You can be sure that the heirs will exactly return the list. haha!
    """
    @staticmethod
    @abc.abstractmethod
    def changed(webdriver_instance: webdriver.Chrome, element_locator) -> []:
        pass
