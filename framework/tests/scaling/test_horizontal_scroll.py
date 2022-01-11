from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import visibility_of
from selenium.common.exceptions import StaleElementReferenceException

from .scaling_scripts import heights_script, boundaries_script, scroll_script
from framework.element import Element


framework_version = 5
WCAG = "1.4.10"
name = """Ensures that there is no horizontal scroll on zoomed pages (from 100% to 300%)"""
depends = []
webdriver_restart_required = True
elements_type = ""
test_data = [
    {"page_info": {"url": "horizontal_scroll/page_ok.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "horizontal_scroll/page_fail.html"}, "expected_status": "FAIL"},
]


def test(webdriver_instance, activity, element_locator):
    """
    Tests a web page for WCAG 2.1 1.4.10 criterion.
    Detects horizontal scroll via asynchronous javascript code execution.
    Gives 'PASS', 'NOTRUN' and 'ERROR' status.
    Parameters of the function satisfy the framework requirements.
        More details on: http://confluence:8090/display/RND/Accessibility+Testing+Framework
    Returns test result as a dict:
    result = {
                'status': <'FAIL', 'PASS' or 'NOTRUN'>,
                'message': <string>,
                'elements': [],
                'checked_elements': []
             }
    """
    return HorizontalScrollTest(webdriver_instance, activity, element_locator).result


class HorizontalScrollTest:
    def __init__(self, webdriver_instance, activity, element_locator):
        self.driver = webdriver_instance
        self.activity = activity
        self.locator = element_locator
        self.zoom_list = [
            "100",
            "110",
            "120",
            "125",
            "133",
            "150",
            "170",
            "175",
            "150",
            "200",
            "240",
            "250",
            "300",
            "400",
        ]

        self.height_values = self._collect_text_node_params()
        self.window_rect = self.driver.execute_script("return window.screen.valueOf();")
        self._main()

    def _main(self):
        self.activity.get(self.driver)
        # iterate over different scaling values
        window_settings = self.set_window()
        problem_zooms = self._problem_zooms(window_settings)
        self.report_result(problem_zooms)

    def set_window(self):
        """
        Generator method responsible for webpage zoom by means of window scaling by 'zoom' times.
        Yields: int: current zoom value window sizes
        """
        for zoom in self.zoom_list:
            width, height = self.window_rect["width"], self.window_rect["height"]
            width, height = map(lambda size: size / int(zoom) * 100, (width, height))
            yield width, height, zoom

    def _collect_text_node_params(self, spec="height"):
        """
        Args: spec (str, optional): task specification. Defaults to 'height'.
        Returns: list: some geometrical parameters to process.
        """
        util_tags = ["self::style", "self::script", "self::code"]
        xpath_string = f"//body//*[normalize-space(text()) and not({' or '.join(util_tags)})]"
        text_nodes = self.locator.get_all_by_xpath(self.driver, xpath_string)
        _text_nodes = []
        for node in text_nodes:
            try:
                node = self.driver.execute_script(
                    "return document.querySelector(arguments[0]);", node.get_selector()
                )
                if visibility_of(node)(self.driver):
                    _text_nodes.append(Element(node, self.driver))
            except StaleElementReferenceException:
                continue
        text_nodes = _text_nodes
        del _text_nodes

        script = heights_script if spec == "height" else boundaries_script
        text_params = self.driver.execute_script(
            script,
            [
                self.driver.execute_script("return document.querySelector(arguments[0]);", node.get_selector())
                for node in text_nodes
            ],
        )

        return text_params

    def direction_scroll(self, alignment):
        """
        Detects horizontal scroll via just comparing scroll and window widths.
        Returns True as from js script if horizontal scroll exists.
        Args:
            alignment (str): horiz / vert specification
        Returns: bool: scroll presence for alignment (direction)
        """
        direction = "left" if alignment == "horizontal" else "top"

        scroll = self.driver.execute_script(scroll_script, self.curr_width)

        return scroll

    def _text_reflow_works(self):
        """
        Method is invoked at every zoom value. In compare with 100% zoom heights, no scroll was there.
        Returns: bool: True if reflow changes in textual nodes height detected, else False
        """
        height_values = self._collect_text_node_params()
        reflowed = [1 for prev, curr in zip(self.height_values, height_values) if prev != curr]
        if not reflowed:
            return False
        return True

    def _scroll_cases_handler(self, align, conclusion=True):
        """
        Instructions set for different cases of scroll detection.
        Conclusion value will elucidate the bug occurrenceю
        Args:
            align (str): horiz /vert scroll trigger
            conclusion (bool): Defaults to True. False if bug event.
        Returns: bool: conclusion True - means any scroll is fine, False - bug
        """
        if align not in {"horizontal", "vertical"}:
            conclusion = self._text_reflow_works()
            return conclusion
        if self.direction_scroll(align):
            if align == "horizontal":
                align = "vertical"
            elif align == "vertical":
                align = "both"
            return self._scroll_cases_handler(align)

        return conclusion

    def _problem_zooms(self, window_params):
        """
        Method collects all zoom iterations where scroll was inappropriate.
        With an exception of warning case.
        fail -> warning transformation can happen directly in report_result method.
        Args: window_params (tuple): current window params
        Returns: list: zoom values to pass to test report
        """
        problem_zooms = []
        for param_set in window_params:
            win_w, win_h, scale = param_set
            self.curr_width = win_w
            self.driver.set_window_rect(width=win_w, height=win_h)
            # check horizontal scroll
            align = "horizontal"
            unexpected_scroll = not self._scroll_cases_handler(align)
            if unexpected_scroll:
                if scale == "100":
                    return ["100"]
                problem_zooms.append(scale)
        return problem_zooms

    def _content_accessible_with_scroll(self, window_width):
        """
        For FAIL case, give last try - checks if all content is inside the window,
        despite of horizontal and vertical scroll presence.
        Args: window_width (str): minimum window width
        Returns: bool: is content accessible or not
        """
        left_boundaries, right_boundaries = set(), set()
        boundaries = self._collect_text_node_params(spec="boundaries")
        for _ in [edges.split() for edges in boundaries]:
            left_boundaries.add(int(_[0]))
            right_boundaries.add(int(_[1]))
        # finished extreme x points collection
        try:
            left_edge, right_edge = min(left_boundaries), max(right_boundaries)
        except ValueError:
            left_edge, right_edge = 0, 10000
        # content is accessible, despite of horizontall scroll
        if right_edge - left_edge <= window_width * 100:
            return True

        return False

    def report_result(self, problem_zooms):
        self.result = {
            "status": "PASS",
            "message": "No issues with scroll",
            "elements": [],
            "checked_elements": [],
        }

        if problem_zooms:
            bad_body = Element(self.driver.execute_script("return document.body;"), self.driver)
            bad_body = {
                "element": bad_body,
                "problem": "Horizontal scroll on page",
                "interaction_sequence": [
                    {"element": bad_body, "action": "zoom", "zoom_percent": problem_zooms[0]}
                ],
            }
            final_scale = problem_zooms[-1]
            problem_zooms = "%, ".join(problem_zooms)
            final_width = self.window_rect["width"] / int(final_scale)
            self.result["status"] = "FAIL"
            self.result["message"] = f"Horizontal scroll detected on {problem_zooms}% zoom."
            self.result["elements"] = [
                bad_body,
            ]
            if self._content_accessible_with_scroll(final_width):
                self.result["status"] = "WARN"
                self.result[
                    "message"
                ] = f"Horizontal scroll detected on {problem_zooms}% zoom. Content seems to be still accessible"
