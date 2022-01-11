import unittest

from selenium import webdriver

from framework import request_limiter
from framework.activity import Activity
from framework.element_locator import ElementLocator, DEFAULT_TARGET_ELEMENTS


@unittest.skip('Deprecated. Will be removed soon')
class ElementLocatorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.webdriver_inst = webdriver.Firefox()
        cls.activity = Activity(
            name='Test Activity',
            url='https://google.com',
            options=None,
            page_after_login=None,
            commands=[]
        )
        limiter = request_limiter.RequestLimiter(0)
        cls.webdriver_inst.limiter = limiter

    @classmethod
    def tearDownClass(cls) -> None:
        cls.webdriver_inst.quit()

    def setUp(self) -> None:
        # TODO rewrite to local file with scripts support
        self.element_locator = ElementLocator(
            activity=self.activity,
            webdriver_instance=self.webdriver_inst,
            target_elements=DEFAULT_TARGET_ELEMENTS
        )

    def test_element_locator_analyze(self):
        self.element_locator.analyze(fake=False)
