import unittest

from framework.libs.background_images import check_image_contain_dot, check_image_contain_elem, find_background_images


class BackgroundImagesTestCase(unittest.TestCase):
    def test_check_image_contain_dot_true(self):
        dot_in = 10, 10
        result = check_image_contain_dot(x_image=0, y_image=0, w_image=100, h_image=100, dot=dot_in)
        self.assertTrue(result)

    def test_check_image_contain_dot_false(self):
        dot_out = 255, 255
        result = check_image_contain_dot(x_image=0, y_image=0, w_image=100, h_image=100, dot=dot_out)
        self.assertFalse(result)

    def test_check_image_contain_elem_true(self):
        result = check_image_contain_elem(x_image=0, y_image=0, w_image=100, h_image=100,
                                          x_elem=10, y_elem=10, w_elem=15, h_elem=15)
        self.assertTrue(result)

    def test_check_image_contain_elem_false(self):
        result = check_image_contain_elem(x_image=0, y_image=0, w_image=100, h_image=100,
                                          x_elem=100, y_elem=100, w_elem=15, h_elem=15)
        self.assertFalse(result)

    @unittest.skip(reason='TODO. Requires more investigation')
    def test_find_background_images(self):
        expected = []
        result = find_background_images(element_locator=None, driver=None, images=[])
        self.assertEqual(result, expected)
