from typing import List
import statistics
from collections import defaultdict

from selenium import webdriver

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.libs.element_rect import WebElementRect
from framework.element import Element
from framework.libs.is_visible import is_visible
from framework.libs.distance_between_elements import distance

framework_version = 4
name = "Ensures that elements that look like data tables are marked up as table semantically"
webdriver_restart_required = False
WCAG = "1.3.1"

elements_type = "table"
test_data = [
    {
        "page_info": {
            "url": "tables/page_good_false_tables.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "tables/page_bugs_false_tables.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    },
    {
        "page_info": {
            "url": "tables/page_bugs_false_tables_2.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 4
    },
    {
        "page_info": {
            "url": "tables/page_bugs_false_tables_3.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]

EPSILON = 0.01
IGNORED_TAGS = ["table", "span"]


def test(webdriver_instance: webdriver, activity: Activity, element_locator: ElementLocator):
    """
    :param element_locator:
    :param activity:
    :param webdriver_instance:
    :return:
    """
    activity.get(webdriver_instance)
    checked_elements, bad_elements = TablesStruct(webdriver_instance, element_locator).find_bad_elements()
    if bad_elements:
        for i, bad in enumerate(bad_elements):
            print(i + 1, bad)
        return dict(status="FAIL", message="There are elements that have a table structure", elements=bad_elements,
                    checked_elements=checked_elements)
    return dict(status="PASS", message="Missing tables with bad struct", checked_elements=checked_elements)


class TablesStruct:

    def __init__(self, driver: webdriver.Firefox, locator: ElementLocator):
        self._dr = driver
        self._loc = locator

    def _wrap(self, el):
        return ElementWrapper(el, self._dr)

    def all_coordinates(self, elements):
        """
        :return: dict with all elements with there coordinates on page
        """
        rect_elements = []

        def get_rect_elements(e: Element):
            wrap = self._wrap(e)
            if wrap.is_visible:
                rect_elements.append(wrap.rect_elem)
        Element.safe_foreach(elements, get_rect_elements)
        return rect_elements

    @staticmethod
    def check_wh(rects: List[WebElementRect], coord_wh: str, force: bool = True, epsilon=EPSILON):
        wh = [getattr(rect, coord_wh) for rect in rects]
        mean_wh = wh[1] if force else statistics.mean(wh)
        return all((abs(i - mean_wh) / mean_wh if mean_wh else i) <= epsilon for i in wh)

    def equals_coord(self, rects: List[WebElementRect], coord: str, coord_wh: str, force: bool):
        """
        This method checks the elements in the list by coordinates,
        the possibility of the table structure of the elements.

        :param force: bool
        :param rects: List with the coordinates of the elements
        :param coord: coordinate to compare (x or y)
        :param coord_wh: value to get the height or width attribute
        :return: True, if the elements have the structure of a table, False if not
        """
        if len(rects) <= 1:
            return False
        if self.check_wh(rects, coord):
            if coord_wh is None:
                return True
            wh = [getattr(rect, coord_wh) for rect in rects]
            median_wh = statistics.median(wh)
            return (all(rect.element().tag_name == rects[1].element().tag_name for rect in rects)
                    and max(wh) / min(wh) < 4.1 and max(wh) / median_wh < 2.3
                    and (not force or sum((abs(getattr(rect, coord_wh) - median_wh) / median_wh if median_wh else
                                           getattr(rect, coord_wh)) <= 0.25 for rect in rects) / len(rects) >= 0.56))
        return False

    def add_bad_element(self, descendants, elements, element, severity):
        descendants.extend(element.find_by_xpath('descendant::*', self._dr))
        elements.append(dict(element=element, problem="This element has a table structure.", severity=severity))

    def find_bad_elements(self):
        """
        This method verifies that the elements have children and
        that these children have children and that they are all equal in x or y coordinate.

        :return: list with elements that have a table structure
        """
        elements = self._loc.get_all_by_xpath(
            self._dr, "//body//*[*[not(ancestor::table) and not(ancestor::ul) and not(ancestor::ol) "
                      "and not (ancestor::*[@role='table']) and not (descendant::table)]]")[::-1]
        bad_elements = []
        descendants_bad_elements = []

        def check(element: Element):
            if element in descendants_bad_elements:
                return
            children = [child for child in element.find_by_xpath("child::*", self._dr) if self._wrap(child).is_visible
                        and self._wrap(child).text.strip() and not child.find_by_xpath("descendant::table", self._dr)]
            if self.check_rows(children, element) or self.check_columns(children, element):
                self.add_bad_element(descendants_bad_elements, bad_elements, element,
                                     severity="WARN" if any(not i.find_by_xpath("child::*", self._dr) for i in children) else "FAIL")
            elif self.check_cells(children, element):
                self.add_bad_element(descendants_bad_elements, bad_elements, element, severity="WARN")
            elif self.check_columns_without_cells(children, element):
                self.add_bad_element(descendants_bad_elements, bad_elements, element, severity="FAIL")
            else:
                descendants = [i for i in element.find_by_xpath("descendant::*[not(child::*) and text()]", self._dr)
                               if self._wrap(i).is_visible and self._wrap(i).text.strip()
                               and not i.find_by_xpath('ancestor-or-self::*[self::ul or self::ol]', self._dr)]
                if len(descendants) < 2 or any(i.tag_name != descendants[1].tag_name for i in descendants):
                    return
                if self.check_cells(descendants, element) or self.check_cells(descendants[1:], element):
                    self.add_bad_element(descendants_bad_elements, bad_elements, element, severity="FAIL")
        Element.safe_foreach(elements, check)
        return elements, self.filter(descendants_bad_elements, bad_elements)

    def check_display(self, element: Element, display: str):
        return element.get_element(self._dr).value_of_css_property('display') == display

    @staticmethod
    def filter(descendants, elements):
        return [e for e in elements if e['element'] not in descendants]

    def check_cells(self, rects: List[Element], el: Element):
        if el.get_parent(self._dr).tag_name in IGNORED_TAGS or el.tag_name in IGNORED_TAGS or len(rects) <= 3:
            return False
        rows = defaultdict(list)
        columns = defaultdict(list)
        for rect in rects:
            location = rect.get_element(self._dr).location
            rows[location['y']].append(rect)
            columns[location['x']].append(rect)
        if len(rows) < 2 or len(columns) < 2:
            return False

        number_of_cells_per_row = None
        for _, row in rows.items():
            if number_of_cells_per_row is None:
                number_of_cells_per_row = len(row)
            elif len(row) != number_of_cells_per_row or len(row) < 2:
                return False
        number_of_cells_per_column = None
        for _, column in columns.items():
            if number_of_cells_per_column is None:
                number_of_cells_per_column = len(column)
            elif len(column) != number_of_cells_per_column or len(column) < 2:
                return False

        correct_rows = 0
        for _, row in rows.items():
            if self.check_coordinates(row, 'y', 'width') and not self.check_coordinates(row, 'x'):
                correct_rows += 1
            if correct_rows / len(rows) > 0.6:
                return True
        return False

    def check_rows(self, rects, el):
        if el.get_parent(self._dr).tag_name in IGNORED_TAGS or el.tag_name in IGNORED_TAGS:
            return False

        if (((len(rects) > 1 and self.equals_coord(self.all_coordinates(rects), 'x', 'height', force=True)
              and (self.check_descendant_tags(rects) or (len(rects) > 2 and self.check_descendant_tags(rects[1:]))))
                or (len(rects) >= 4 and self.equals_coord(self.all_coordinates(rects[1:-1]), 'x', 'height', force=True)))
                or (len(rects) == 1 and self.check_display(rects[0], 'table-row') and self.check_display(el, 'table'))):
            correct_rows = 0
            width_of_cells_in_row = None
            for i, row in enumerate(rects):
                for cells in [row.find_by_xpath("child::*", self._dr),
                              row.find_by_xpath("child::*[not(child::*) and text()]", self._dr)]:
                    cells = [e for e in cells
                             if is_visible(e, self._dr) and min(e.get_element(self._dr).size.values()) > 5]
                    if len(cells) < 2:
                        continue
                    if len(rects) == 1:
                        return (all(self.check_display(cell, 'table-cell') for cell in cells)
                                and self.equals_coord(self.all_coordinates(cells), 'y', 'width', True)
                                and self.check_wh(self.all_coordinates(cells), 'height'))

                    if width_of_cells_in_row is not None and len(cells) != len(width_of_cells_in_row):
                        continue

                    if self.check_coordinates(cells, 'y', 'width') and not self.check_coordinates(cells, 'x'):
                        widths = [cell.get_element(self._dr).size['width'] for cell in cells]
                        if width_of_cells_in_row is None and i:
                            width_of_cells_in_row = widths
                        if width_of_cells_in_row is None or self.compare_sizes(width_of_cells_in_row, widths):
                            correct_rows += 1
                        break
                if correct_rows / len(rects) > 0.6:
                    return True
            return correct_rows / len(rects) > 0.6
        return False

    @staticmethod
    def compare_sizes(size_first: List[float], size_second: List[float]):
        return all(abs(i - j) < 100 for i, j in zip(size_first, size_second))

    def check_columns_without_cells(self, rects, el):
        if el.get_parent(self._dr).tag_name in IGNORED_TAGS or el.tag_name in IGNORED_TAGS or len(rects) < 3:
            return False
        return ('table' in el.source and 'aria-multiselectable' not in el.source
                and self.check_wh(self.all_coordinates(rects), 'y', force=False, epsilon=0.09)
                and self.check_wh(self.all_coordinates(rects), 'width')
                and self.check_wh(self.all_coordinates(rects), 'height', force=False, epsilon=0.06)
                )

    def check_columns(self, rects, el):
        if el.get_parent(self._dr).tag_name in IGNORED_TAGS or el.tag_name in IGNORED_TAGS or len(rects) <= 1:
            return False
        if any(not column.find_by_xpath("child::*", self._dr) for column in rects) and len(rects) > 2:
            return (all(distance(self._dr, i, j) < 1 for i, j in zip(rects, rects[1:]))
                    and self.check_descendant_tags(rects)
                    and (self.check_wh(self.all_coordinates(rects), 'width')
                         or self.check_wh(self.all_coordinates(rects), 'height'))
                    and self.check_coordinates(rects, 'y', 'width'))

        if self.equals_coord(self.all_coordinates(rects), 'y', 'width', force=True):
            correct_columns = 0
            number_of_rows = None
            for column in rects:
                for cells in [column.find_by_xpath("child::*[not(child::*) and text()]", self._dr),
                              column.find_by_xpath("child::*", self._dr)]:
                    cells = [e for e in cells
                             if is_visible(e, self._dr) and min(e.get_element(self._dr).size.values()) > 5]
                    if len(cells) < 2:
                        continue
                    if self.check_coordinates(cells, 'x', 'height') and not self.check_coordinates(cells, 'y') \
                            and self.check_descendant_tags(cells) and (
                            len(cells) == number_of_rows or number_of_rows is None):
                        correct_columns += 1
                        number_of_rows = len(cells) if number_of_rows is None else number_of_rows
                        break
                if correct_columns / len(rects) > 0.6:
                    return True
        return False

    def check_coordinates(self, rects, coord, attribute=None, force=False):
        """
        :param force: bool
        :param rects: List with the coordinates of the elements
        :param coord: coordinate to compare (x or y)
        :param attribute: value to get the height or width attribute
        """
        if len(rects) <= 1:
            return False
        return self.equals_coord(self.all_coordinates(rects), coord, attribute, force)

    def check_descendant_tags(self, rects):
        """
        :param rects: List with the coordinates of the elements
        :return:
        """
        if len(rects) <= 1:
            return False

        def get_descendant_tags(elem: Element):
            return set(d.tag_name for d in elem.find_by_xpath('descendant-or-self::*', self._dr))

        sample_tags = get_descendant_tags(rects[1])
        return all(sample_tags == get_descendant_tags(rect) for rect in rects)
