from string import whitespace

from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.element import Element

framework_version = 4
name = "Ensures that elements that look like text tables are found."
webdriver_restart_required = False
WCAG = "1.3.1"

elements_type = "table"
test_data = [
    {
        "page_info": {
            "url": "tables/text/page_good.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tables/text/page_bug_1.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    },
    {
        "page_info": {
            "url": "tables/text/page_bug_3.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    },
    {
        "page_info": {
            "url": "tables/text/page_bug_4.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    },
    {
        "page_info": {
            "url": "tables/text/page_bug_5.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 5
    },
]


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator):
    """
    :param element_locator:
    :param activity:
    :param webdriver_instance:
    :return:
    """
    activity.get(webdriver_instance)
    checked_elements, bad_elements = TextTables(webdriver_instance, element_locator).find_bad_elements()
    if bad_elements:
        for i, bad in enumerate(bad_elements):
            print(i + 1, bad)
        return dict(status="FAIL", message="Text tables were found.", elements=bad_elements,
                    checked_elements=checked_elements)
    return dict(status="PASS", message="Text tables were not found.", checked_elements=checked_elements)


class TextTables:

    def __init__(self, driver, locator):
        self._dr = driver
        self._loc = locator

    def _wrap(self, el):
        return ElementWrapper(el, self._dr)

    @staticmethod
    def split(line):
        list_ = []
        element = ''
        for ch in line:
            if ch not in whitespace and element and element[-1] in whitespace:
                list_.append(element)
                element = ch
            else:
                element += ch
        list_.append(element)
        return list_

    def compare_lines(self, line1, line2):
        words1 = self.split(line1)
        words2 = self.split(line2)
        if len(words1) < 2 or len(words2) < 2 or len(words1) != len(words2):
            return False
        return all(len(word1) == len(word2) and self.number_of_whitespace_symbols(word1) > 1
                   and self.number_of_whitespace_symbols(word2) > 1 for word1, word2 in zip(words1[:-1], words2[:-1]))

    @staticmethod
    def number_of_whitespace_symbols(line):
        counter = 0
        len_ = 0
        for ch in line:
            if ch in whitespace:
                len_ += 1
            elif len_:
                if len_ > 1:
                    counter += 1
                len_ = 0
        return counter

    def contains_duplicate_whitespace_symbols(self, line1, line2):
        line1 = line1.strip()
        line2 = line2.strip()
        if not line1 or not line2:
            return False
        number_line1 = self.number_of_whitespace_symbols(line1)
        number_line2 = self.number_of_whitespace_symbols(line2)
        return number_line1 > 0 and number_line1 == number_line2

    @staticmethod
    def contains_duplicate_vertical_line(line1, line2):
        return abs(line1.count('|') - line2.count('|')) <= 1 and line1.count('|') > 2 and line2.count('|') > 2

    def detect_text_table(self, element: Element):
        lines = [line for line in element.get_text(self._dr).split('\n') if line.replace('-', '').replace('|', '').strip()]
        if len(lines) < 2:
            return ""
        table = []
        severity = "WARN"
        for line1, line2 in zip(lines, lines[1:]):
            if self.compare_lines(line1, line2):
                severity = "FAIL"
                table.extend([line1, line2] if not table else [line2])
            elif self.contains_duplicate_whitespace_symbols(line1, line2) or self.contains_duplicate_vertical_line(line1, line2):
                table.extend([line1, line2] if not table else [line2])
            else:
                if len(table) > 1:
                    return severity
                table = []
        return severity if len(table) > 1 else ""

    def find_bad_elements(self):
        elements = self._loc.get_all_by_xpath(self._dr, "//body//*[text()]")
        bad_elements = []

        def check(element: Element):
            severity = self.detect_text_table(element)
            if severity:
                bad_elements.append(dict(element=element, problem="This element can contain a text table.", severity=severity))
        Element.safe_foreach(elements, check)
        return elements, self.filter(bad_elements)

    def filter(self, elements):
        descendants = sum([e['element'].find_by_xpath('ancestor::*', self._dr) for e in elements], [])
        return [e for e in elements if e['element'] not in descendants]
