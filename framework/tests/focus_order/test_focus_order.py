from collections import defaultdict

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.libs.test_pattern import SuperTest
from framework.screenshot.screenshot import Screenshot

from framework.libs.test_pattern import wrap_test_output

__all__ = []

framework_version = 4
WCAG = "2.4.3"
name = "Ensures that the focus order is logical, visually hidden elements do not receive focus, " \
       "and there is no keyboard trap (2.1.2, 2.4.3)"
depends = []
webdriver_restart_required = False
locator_required_elements = []
elements_type = ""
test_data = [
    {
        "page_info": {"url": r"focus/page_good_focus_order.html"},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r"focus/page_bugs_focus_order.html"},
        "expected_status": "FAIL"
    },
    {
        "page_info": {"url": r"page_noelements.html"},
        "expected_status": "NOELEMENTS"
    },
]
TOLERANCE = 20
TEST_MESSAGE = "Some elements have incorrect focus order and/or there is a keyboard trap"


# @wrap_test_output
def test(webdriver_instance: webdriver, activity, element_locator: ElementLocator, dependencies=None):
    return SequenceTest(webdriver_instance, activity, element_locator, dependencies).get_result()


class SequenceTest(SuperTest):
    def __init__(self, webdriver_instance, activity, locator, dependencies):
        super().__init__(webdriver_instance, activity, locator, dependencies)
        self.screenshot = Screenshot(driver=self.driver, elements=list())
        self._main()
        self.combine_multiple_bugs()

    def find_first_element(self) -> Element:
        """ Return fist WebElement is the <body> """
        body = self.locator.get_all_by_xpath(self.driver, "//body")[0]
        body = body.get_element(self.driver)
        body.send_keys(Keys.TAB)
        first_focusable = self.driver.switch_to_active_element()
        # print('First:', first_focusable.get_attribute('outerHTML'))
        # print()
        return Element(first_focusable, self.driver)

    def _main(self):
        """ Check that elements receive focus in order "from up to down" and "from left to right".

        """
        try:
            first_focusable = self.find_first_element()
        except NoSuchElementException:  # Status - "NOELEMENTS"
            return
        if first_focusable.tag_name == "body":  # Status - "NOELEMENTS"
            return
        self.set_pass_status()
        prev_element = first_focusable

        if not first_focusable.is_displayed(self.driver):
            # print("first no display")
            self.report_hidden_focus(first_focusable, severity="FAIL")
            last_visible_element = None
        else:
            last_visible_element = first_focusable

        while True:
            prev_element.get_element(self.driver).send_keys(Keys.TAB)
            curr_element = Element(self.driver.switch_to_active_element(), self.driver)
            # print('Current: ', self.get_attribute(curr_element, 'outerHTML')[:80:])

            if self.screenshot.it_infinity():
                # print('Infinity page exit')
                break

            elif curr_element in self.result["checked_elements"][:-1:] and \
                    curr_element.tag_name not in ('iframe', 'body') and curr_element == prev_element:
                self.report_keyboard_trap(curr_element)
                # if not self.avoid_keyboard_trap(curr_element):
                # print('Keyboard trap exit')
                break

            elif curr_element == first_focusable and curr_element.tag_name != 'iframe' or \
                    curr_element in self.result["checked_elements"][:-1:] or curr_element.tag_name == 'body':
                # print('Expected exit')
                break

            if last_visible_element:
                curr_xy = self.get_element_center_coord(self.get_rect(curr_element))
                prev_xy = self.get_element_center_coord(self.get_rect(prev_element))
                # print("____________________________________________________________________")
                # print('Curr position: ', curr_xy)
                # print('Prev position: ', prev_xy)

            """ Hidden element check"""
            if not curr_element.is_displayed(self.driver) and not last_visible_element:
                # print("not displayed")
                self.report_hidden_focus(curr_element, severity="WARN")
            elif not self.check_parent_css(curr_element):
                # print("Incorrect parent opacity")
                self.report_hidden_focus(curr_element, severity="WARN")
            elif last_visible_element and (prev_xy[0] < 0 or prev_xy[1] < 0) and last_visible_element != first_focusable:
                # print("PREV x or y < 0")
                # print(prev_xy)
                self.report_hidden_focus(curr_element, severity="FAIL")
            elif int(self.get_rect(curr_element)['width']) * (self.get_rect(curr_element)['height']) < 100:
                # print("size < 100")
                self.report_hidden_focus(curr_element, severity="FAIL")
            else:
                """ Direction check """
                if last_visible_element and any([
                            self.upward(prev_xy, curr_xy),
                            self.upward_left(prev_xy, curr_xy),
                            self.upward_right(prev_xy, curr_xy),
                            self.right_to_left(prev_xy, curr_xy)
                        ]):
                    self.report_focus_order(prev_element)

                last_visible_element = curr_element

            self.result["checked_elements"].append(prev_element)
            prev_element = curr_element
            # print()

    def report_focus_order(self, element, severity="WARN"):
        # print("FOCUS ORDER ", severity)
        # print(element.source)
        # print("RECT:")
        # print(self.get_rect(element))
        # print("_"*80)
        # print()
        self.report_issue(
            element=element,
            problem_message="The next element after that element receive focus in incorrect order",
            error_id="IncorrectFocusOrder",
            severity=severity,
            test_message=TEST_MESSAGE,
        )

    def report_keyboard_trap(self, element):
        # print("TRAP BUG")
        # print(element.source)
        # print("_" * 80)
        # print()
        self.report_issue(
            element=element,
            problem_message="Keyboard focus can't be moved away from the component using only a keyboard interface",
            error_id="KeyboardTrap",
            severity="FAIL",
            test_message=TEST_MESSAGE,
        )

    def report_hidden_focus(self, element, severity):
        # print("HIDDEN ELEMENT BUG")
        # print(element.source)
        # print("_" * 80)
        # print()
        self.report_issue(
            element=element,
            problem_message="The element is not presented for a user but able to receive focus using a keyboard",
            error_id="FocusableHiddenElement",
            severity=severity,
            test_message=TEST_MESSAGE,
        )

    @staticmethod
    def get_element_center_coord(rect):
        return int(rect['x']) + rect['width']//2, int(rect['y']) + rect['height']//2

    @staticmethod
    def upward_left(prev_xy: tuple, curr_xy: tuple) -> bool:
        return curr_xy[0] < prev_xy[0] and curr_xy[1] < prev_xy[1]

    @staticmethod
    def upward_right(prev_xy: tuple, curr_xy: tuple) -> bool:
        return curr_xy[0] > prev_xy[0] and curr_xy[1] + TOLERANCE < prev_xy[1]

    @staticmethod
    def upward(prev_xy: tuple, curr_xy: tuple) -> bool:
        return prev_xy[0] - TOLERANCE < curr_xy[0] < prev_xy[0] + TOLERANCE and curr_xy[1] < prev_xy[1]

    @staticmethod
    def right_to_left(prev_xy: tuple, curr_xy: tuple) -> bool:
        return curr_xy[0] < prev_xy[0] and prev_xy[1] - TOLERANCE < curr_xy[1] < prev_xy[1] + TOLERANCE

    def check_parent_css(self, element) -> bool:
        last_ten_parents = element.find_by_xpath("ancestor::*", self.driver)[-10::]
        for el in last_ten_parents:
            el = el.get_element(self.driver)
            if el.tag_name == "body":
                continue
            if el.value_of_css_property("opacity") == 0:
                return False
            if el.value_of_css_property("left") != "auto" and int(float(el.value_of_css_property("left")[:-2:])) < 0:
                return False
        return True

    def combine_multiple_bugs(self):
        elements = defaultdict(list)
        sorted_bugs = list()
        # print("TOTAL BUGS {}".format(len(self.result["elements"])))
        for data in self.result["elements"]:
            elements[data["element"].tag_name].append(data)

        for tag in elements.keys():
            if len(elements[tag]) > 10:
                coordinates = defaultdict(list)
                for data in elements[tag]:
                    rect = self.get_rect(data["element"])
                    coordinates[int(rect["y"])].append(data)
                for coord in coordinates.keys():
                    if len(coordinates[coord]) > 3:
                        bug_data = coordinates[coord][0]
                        bug_data["problem_message"] = f"Multiple bugs for {tag} elements"
                        # print("UNION")
                        # for el in coordinates[coord]:
                        #     print(el["element"].source)
                        sorted_bugs.append(bug_data)
                    else:
                        sorted_bugs.extend(coordinates[coord])
            else:
                sorted_bugs.extend(elements[tag])
        # print("FINAL BUGS {}".format(len(sorted_bugs)))
        self.result["elements"] = sorted_bugs

    # def avoid_keyboard_trap(self, trap_element):
    #     clickable = self.locator.get_all_by_xpath(self.driver, "//button")
    #     clickable.extend(self.locator.get_all_by_xpath(self.driver, "//a"))
    #     # tr_x = self.get_rect(trap_element)["x"]
    #     tr_y = self.get_rect(trap_element)["y"]
    #     print("TRY TO AVOID KEYBOATD TRAP")
    #     print("Tr y: ", tr_y)
    #     for element in clickable:
    #         if self.get_rect(element)["y"] > tr_y:
    #             self.send_keys(element, Keys.TAB)
    #             if Element(self.driver.switch_to_active_element(), self.driver) != trap_element:
    #                 print("AVOIDED KEYBOARD TRAP")
    #                 print("ELEM")
    #                 print(element.source[:80])
    #                 print("COORD Y: ", self.get_rect(element)["y"])
    #                 return True
    #     print("FAILED TO AVOID KEYBOARD TRAP")
    #     return False
