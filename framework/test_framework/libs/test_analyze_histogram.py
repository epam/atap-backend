import unittest

from framework.libs.analyze_histogram import analyze_histogram


class AnalyzeHistogramTestCase(unittest.TestCase):
    def test_analyze_histogram_none(self):
        result = analyze_histogram(colors_histogram=None)
        self.assertIsNone(result)

    def test_analyze_histogram_flag_true(self):
        expected = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
        colors_histogram = [c / 10 for c in range(0, 10)]
        result = analyze_histogram(colors_histogram=colors_histogram, flag=True)
        self.assertEqual(result, expected)

    def test_analyze_histogram_flag_false(self):
        expected = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
        colors_histogram = [c / 10 for c in range(0, 10)]
        result = analyze_histogram(colors_histogram=colors_histogram, flag=False)
        self.assertEqual(result, expected)
