import copy
import unittest

from selenium import webdriver

from framework.element import Element


class ElementTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.webdriver_inst = webdriver.Firefox()
        # TODO rewrite to local file with scripts support
        cls.webdriver_inst.get('https://google.com')
        cls._element_name = 'q'
        cls.search_box = cls.webdriver_inst.find_element_by_name(cls._element_name)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.webdriver_inst.quit()

    def setUp(self) -> None:
        self.search_box_element = Element(self.search_box, self.webdriver_inst)

    def test_element_equal(self):
        self.assertEqual(self.search_box_element, self.search_box_element)
        self.assertFalse(self.webdriver_inst == self.search_box_element)

    def test_element_deepcopy(self):
        search_box_element_copy = copy.deepcopy(self.search_box_element)
        self.assertNotEqual(id(search_box_element_copy), id(self.search_box_element))
        self.assertEqual(search_box_element_copy.source, self.search_box_element.source)
        self.assertEqual(search_box_element_copy.element_id, self.search_box_element.element_id)

    def test_element_get_element(self):
        element = self.search_box_element.get_element(self.webdriver_inst)
        self.assertEqual(self.search_box_element.element[id(self.webdriver_inst)], element)

    def test_element_get_parent(self):
        parent_element = self.search_box_element.get_parent(self.webdriver_inst)
        self.assertEqual(parent_element.tag_name, 'div')

    def test_element_get_attributes(self):
        element_attributes = self.search_box_element.get_attributes(self.webdriver_inst)
        self.assertEqual(element_attributes['name'], self._element_name)
        self.assertEqual(element_attributes['type'], 'text')

    def test_element_find_by_xpath(self):
        elements = self.search_box_element.find_by_xpath('//head//*', self.webdriver_inst)
        self.assertTrue(elements)
        no_elements = self.search_box_element.find_by_xpath('wrong_xpath', self.webdriver_inst)
        self.assertEqual(no_elements, [])

    def test_is_same_page(self):
        is_same = self.search_box_element.is_same_page('https://google.com', 'https://google.com')
        self.assertTrue(is_same)
        is_not_same = not self.search_box_element.is_same_page('https://google.com/doodles', 'https://google.com/')
        self.assertTrue(is_not_same)

    def test_is_same_site(self):
        is_same = self.search_box_element.is_same_site('https://google.com', 'https://google.com')
        self.assertTrue(is_same)
        is_not_same = not self.search_box_element.is_same_site('https://google.com', 'https://apple.com')
        self.assertTrue(is_not_same)
