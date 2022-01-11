import json
import unittest
from unittest import mock
from unittest.mock import MagicMock

from selenium import webdriver

from framework import activity, request_limiter
from framework.activity import Activity
from framework.element import Element


@mock.patch('time.sleep', return_value=None)
class ActivityTestCase(unittest.TestCase):
    pass
    # @classmethod
    # def setUpClass(cls, *args, **kwargs) -> None:
    #     cls.webdriver_inst = webdriver.Firefox()
    #     limiter = request_limiter.RequestLimiter(0)
    #     cls.webdriver_inst.limiter = limiter
    #
    # @classmethod
    # def tearDownClass(cls, *args, **kwargs) -> None:
    #     cls.webdriver_inst.quit()
    #
    # def setUp(self, *args, **kwargs) -> None:
    #     self.url = 'https://google.com'
    #     self.options = json.dumps(
    #         {'auth_required': False,
    #          'auth_setting': '{"login": "", "activator": ""}'}
    #     )
    #     self.activity = Activity(name='Main Activity',
    #                              url=self.url,
    #                              options=self.options,
    #                              page_after_login=False,
    #                              commands=[])
    #
    # def test_camel_case_to_snake_case(self, *args, **kwargs):
    #     camel_case = 'SnakeCase'
    #     snake_case = activity.camel_case_to_snake_case(camel_case)
    #     self.assertEqual(snake_case, 'snake_case')
    #
    # def test_snake_case_to_camel(self, *args, **kwargs):
    #     snake_case = 'camel_case'
    #     camel_case = activity.snake_case_to_camel(snake_case)
    #     self.assertEqual(camel_case, 'camelCase')
    #
    # def test_load_activities(self, *args, **kwargs):
    #     page_info = {'url': self.url,
    #                  'name': 'Main Page',
    #                  'options': self.options,
    #                  'page_after_login': False}
    #     page_activities = activity.load_activities(page_info, self.webdriver_inst)
    #     self.assertTrue(isinstance(page_activities[0], Activity))
    #
    # def test_activity_ignore_command(self, *args, **kwargs):
    #     result = self.activity.ignore_command(number_of_command=0, current_command={'command': 'open'})
    #     self.assertTrue(result)
    #     result1 = self.activity.ignore_command(number_of_command=2, current_command={'command': 'open'})
    #     self.assertFalse(result1)
    #
    # def test_activity_get(self, *args, **kwargs):
    #     self.activity.commands = [
    #         {
    #             'target': None,
    #             'targets': None,
    #             'value': None,
    #             'command': 'close_popup'
    #         }
    #     ]
    #
    #     result = self.activity.get(webdriver_instance=self.webdriver_inst, try_again=False)
    #     self.assertIsNone(result)
    #
    # def test_activity_open(self, *args, **kwargs):
    #     result = self.activity.open(driver=self.webdriver_inst, state={}, target='', targets=(), value=None)
    #     self.assertIsNone(result)
    #
    # def test_activity_close(self, *args, **kwargs):
    #     local_driver = webdriver.Firefox()
    #     result = self.activity.close(driver=local_driver, state={}, target='', targets=(), value=None)
    #     self.assertIsNone(result)
    #     local_driver.quit()
    #
    # def test_activity_run_script(self, *args, **kwargs):
    #     result = self.activity.run_script(driver=self.webdriver_inst, state={}, target='', targets=(), value=None)
    #     self.assertIsNone(result)
    #
    # @unittest.skip(reason='Will be realized later. Got IndexError: Cannot choose from an empty sequence')
    # def test_activity_close_popup(self, *args, **kwargs):
    #     result = self.activity.close_popup(driver=self.webdriver_inst, state={}, target='', targets=(), value=None)
    #     self.assertIsNone(result)
    #
    # def test_activity_wait_for_popup(self, *args, **kwargs):
    #     result = self.activity.wait_for_popup(driver=self.webdriver_inst, state={}, target='', targets=(), value=None)
    #     self.assertIsNone(result)
    #
    # def test_activity_scroll_to_coors(self, *args, **kwargs):
    #     result = self.activity.scroll_to_coors(driver=self.webdriver_inst, x=0, y=0)
    #     self.assertIsNone(result)
    #
    # def test_activity_try_send_keys(self, *args, **kwargs):
    #     element_mock = MagicMock()
    #     value = 'test'
    #     result = self.activity.try_send_keys(elem=element_mock, value=value)
    #     element_mock.send_keys.assert_called_with(value)
    #     self.assertIsNone(result)
    #
    # def test_activity_send_keys(self, *args, **kwargs):
    #     target_mock = MagicMock()
    #     target_mock.__getitem__.return_value = 'xpath'
    #     result = self.activity.send_keys(
    #         driver=self.webdriver_inst, state={}, target=target_mock, targets=(), value=None
    #     )
    #     target_mock.find.assert_called_with('=')
    #     self.assertEqual(result, 'The element was not found on the page.')
    #
    # def test_activity_click_attempt(self, *args, **kwargs):
    #     element_mock = MagicMock()
    #     result = self.activity.click_attempt(element=element_mock)
    #     element_mock.click.assert_called()
    #     self.assertIsNone(result)
    #
    # def test_activity_click(self, *args, **kwargs):
    #     target_mock = MagicMock()
    #     target_mock.__getitem__.return_value = 'xpath'
    #     result = self.activity.click(
    #         driver=self.webdriver_inst, state={}, target=target_mock, targets=(), value=None
    #     )
    #     target_mock.find.assert_called_with('=')
    #     self.assertEqual(result, 'The element was not found on the page.')
    #
    # @unittest.skip(reason='Will be realized later (Already covered)')
    # def test_activity_try_to_get_elements(self, *args, **kwargs):
    #     self.assertIsNone(None)
    #
    # @unittest.skip(reason='Will be realized later (Already covered)')
    # def test_activity_get_element_from_target(self, *args, **kwargs):
    #     self.assertIsNone(None)
