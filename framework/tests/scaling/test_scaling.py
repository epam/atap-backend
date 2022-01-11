import re

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.screenshot.screenshot import Screenshot
from framework.libs.hide_cookie_popup import hide_cookie_popup

from .scaling_scripts import (
    content_preselection_script,
    preselection_js,
    content_recording_js,
    collisions_runaways_script,
    content_violations_js,
    element_sensible_attributes_script,
    execute_on_promise_script,
    cleanup_js,
    warning_collisions_js,
    warning_extinctions_js,
    warning_escapes_js,
)
from framework.js_conductor import CompoundJavascriptEngager, eval_js
from framework.tests.checkbox.test_checkbox_base import _fix_numeral_selector


framework_version = 5
WCAG = "1.4.4, 1.4.10"
name = "Ensures that content is accessible and there are no collisions on zoomed pages - from 100% to 200% and up to 400% zoom"
depends = []
webdriver_restart_required = True
elements_type = ""
test_data = [
    {"page_info": {"url": "scaling/page_good_scaling.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "scaling/page_bugs_scaling.html"}, "expected_status": "FAIL"},
]


def message2error(err):
    err = err[:20]
    return {
        "This element crossed": "WindowLeft",
        "Collision between th": "ReflowCollision",
        "This element vanishe": "ContentVanished",
    }.get(err)


# TODO check execution time
def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    """
    Tests a web page mainly for for WCAG 2.1 1.4.10 criterion. WCAG 2.1 1.4.4 criterion optionally.
    Detects visible and sensible for user accessibility webelements collisions
    and violations of window borders. Detects elements extinctions with no alternatives either.
    Simulates zoom changes from 100% to 200%, then from 200% to 400% if there are no problems until 200%.
    Almost any scale can be handled, as it is implemented with setting of window size.
    Does not account collisions of transparent containers ans so on.
    Accounts text, images, buttons, animations... of their minimal rectangle dimensions.
    Some other elements collisions, e.g. svg or span without a role, are reported in general list of warnings.
    Test primarily implemented in javascript. Some results postprocessing is done here.
    Gives 'PASS', 'NOTRUN' and 'FAIL' status.
    Parameters of the function satisfy the framework requirements.
        More details on: http://confluence:8090/display/RND/Accessibility+Testing+Framework
    Returns test result as a dict:
    result = {
                'status': <'FAIL', 'PASS' or 'NOTRUN'>,
                'problem': <string>,
                'element': [{'element': <element>,
                'problem': <string>[collision with <element> or outside window],
                'error_id': <string>,
                'severity': <string>,
                },
                ],}
    """
    return ScalingReflowTest(webdriver_instance, activity, element_locator).result


class ScalingReflowTest(CompoundJavascriptEngager):
    select_js = "return document.querySelector(arguments[0]);"

    def __init__(self, webdriver_instance, activity, element_locator, timeout=140):
        scripts = [
            execute_on_promise_script,
            content_preselection_script,
            collisions_runaways_script,
            element_sensible_attributes_script,
            preselection_js,
            content_recording_js,
            content_violations_js,
        ]
        script_names = [
            "onPromise",
            "content",
            "collisionsRunaways",
            "customElemAttrs",
            "contentContainer",
            "contentCollection",
            "collisionsCollection",
        ]
        super().__init__(
            webdriver_instance,
            activity,
            element_locator,
            scripts=scripts,
            script_names=script_names,
            timeout=timeout,
        )
        # self.zoom_list = ["100", "170", "200"]
        # self.zoom_list_extra = ["400"]
        self.zoom_list = [
            "100",
            "110",
            "120",
            "125",
            "133",
            "150",
            "170",
            "175",
            "200",
        ]
        self.zoom_list_extra = [
            "240",
            "250",
            "300",
            "400",
        ]
        # * use window params of testing machine, still possible to set constants
        self.window_rect = self.driver.execute_script("return window.screen.valueOf();")
        self.collisions, self.escapes, self.extinctions = {}, {}, {}
        self.decorative_warnings = dict()

        self.content_nodes_info = {}

        self.result = dict(
            status="PASS",
            message="No problems after zoom to 200%",
            elements=[],
            checked_elements=[],
            problem_zooms=[],
        )
        self._main()

    def try_locate_reported(self, reported_selectors):
        """[summary]
        Args:
            reported_selectors (list): selectors list

        Returns:
            list: selectors list
        """
        located_fails = []

        for fail in reported_selectors:
            try:
                self.driver.find_element_by_css_selector(fail)
                located_fails.append(fail)
            except (NoSuchElementException, StaleElementReferenceException):
                print("Lost element", fail)

        return located_fails

    def report_result(self):
        """
        Webelements collisions, screen border violations and lost content without alternatives
        Two test report cases:
            1. bugs occurred before 200% zoom value
            2. no bugs before 200% zoom value, so can be from 200% to 400%
        """
        self.decorative_warnings = self.driver.execute_script("return window.warningsResult;")

        if self.result["problem_zooms"]:
            bug_value = "1.4.4, 1.4.10" if int(self.result["problem_zooms"][0]) <= 200 else "1.4.4"
            bug_start_zoom = self.result["problem_zooms"][0]
            problem_zooms = "%s" % (("%, ").join(self.result["problem_zooms"]))
            self.result["status"] = "FAIL"
            self.result[
                "message"
            ] = f"Irrelevant reflows detected on {problem_zooms}% zoom: bug {bug_value}; errors from {bug_start_zoom}%"
        if self.decorative_warnings:
            self.decorative_handler_warnings()

        print("*****************************************RESULT****************************************")
        print(self.result)

    def _main(self):
        self.activity.get(self.driver)
        self.register_js(self.register_script, self.onpage_scripts)
        self.prepare_content_data()
        hide_cookie_popup(
            self.driver, self.activity, target_element=self.driver.execute_script("return document.body;")
        )
        self.collect_scaling_collisions()
        self.wrap_failed_results()
        self.report_result()

    def update_elem(self, elem: Element, prop="framework_element"):
        selector = elem.get_selector()
        element = self.driver.execute_script(self.select_js, selector)
        framework_element = Element(element, self.driver)

        return locals().get(prop)

    def prepare_content_data(self):
        """
        Include necessary scripts from scaling_scripts in "job scope"
        Set timeouts for async js runs
        """
        js_async_wrap = "window.Timeout(arguments[0], `{}`, `{}`, {});"

        eval_js(
            "onPromise",
            recorder=self.fetch_script_source,
            evaluator=self.execute_script_eval,
            eval_confirm_async=map(
                self.driver.execute_async_script,
                [js_async_wrap.format("true", "true", "50")],
            ),
        )
        eval_js(
            "content",
            "collisionsRunaways",
            "customElemAttrs",
            recorder=self.fetch_script_source,
            evaluator=self.execute_script_eval,
            eval_confirm_async=map(
                self.driver.execute_async_script,
                [
                    js_async_wrap.format(
                        """window.animatedNodes !== undefined && window.RunawaysObserver !== undefined
                    && window.collectCollisions !== undefined && window.hideFixed !== undefined""",
                        "true",
                        "50",
                    )
                ],
            ),
        )

        content_base_timeouts = [
            ["window.animationsEnded == true", "window.animatedNodes", "3000"],
            ["window.contentNotToCross !== undefined", "window.scaleFollowedContent[100]", "25"],
            ["window.extinctionsResult !== undefined", "window.warningsResult.collisions", "25"],
        ]
        self.content_base_timeouts = [*map(lambda t: js_async_wrap.format(*t), content_base_timeouts)]
        content_timeouts = [
            [
                "window.textNodes !== undefined && window.contentNotToCross.size > 0",
                "window.contentNotToCross",
                "50",
            ],
            ["window.interactiveContent !== undefined", "window.interactiveContent", "25"],
            ["window.visibleElements !== undefined", "window.visibleElements.length", "50"],
            ["window.stylesProhibited !== undefined", "window.stylesProhibited", "25"],
            ["window.contentNotToCross.decorative instanceof Set;", "true", "25"],
        ]
        self.content_timeouts = [*map(lambda t: js_async_wrap.format(*t), content_timeouts)]
        collisions_timeouts = [
            ["true", "true", "2000"],
            ["window.collisionsCollected == true", "window.collisionsResultFoot", "100"],
            ["true", "true", "2000"],
            ["window.collisionsCollected == true", "window.collisionsResultHead", "100"],
            ["window.collisionsCollected == true", "window.collisionsResult", "100"],
            [
                "window.runawaysOfZoomPickerDecorative !== undefined",
                "window.runawaysOfZoomPicker.rootObserver",
                "25",
            ],
            [
                "window.runawaysOfZoomPicker.targets.length ==="
                "window.scaleFollowedContent[100].functional.length +"
                "window.scaleFollowedContent[window.zoom].functional.length",
                "window.runawaysOfZoomPicker.viewport",
                "50",
            ],
            ["true", "true", "100"],
            ["true", "true", "100"],
        ]
        self.collisions_timeouts = [*map(lambda t: js_async_wrap.format(*t), collisions_timeouts)]

    def run_chopped_js(self, head_script, timeouts):
        for _, t in zip(
            head_script.split("**************************************************************"),
            timeouts,
        ):
            self.driver.execute_script(_)
            self.driver.execute_async_script(t)

    def run_for_param_set(self, arguments, extended):
        for param_set in self.set_window(extended=extended):
            win_w, win_h, zoom = param_set
            self.driver.execute_script("window.zoom = arguments[0];", zoom)
            self.driver.set_window_rect(width=win_w, height=win_h)

            self.run_chopped_js(*arguments)

            # TODO erase
            # a, b, c = self.fetch_chosen_zoom_bugs(zoom)
            # if len(a) or len(b) or len(c):
            #     self.save_page(f"bugs_{zoom}")

    def collect_scaling_collisions(self, extended=False):
        """
            Run registered js scripts by running other js - "window scope" js scripts
        Args:
            window_params (tuple): params to toggle zoom in behavior
        """
        zoom_list = extended and self.zoom_list_extra or self.zoom_list
        self.driver.execute_script("window.zoomList = arguments[0];", self.zoom_list + self.zoom_list_extra)
        if not extended:
            self.run_chopped_js(preselection_js, self.content_base_timeouts)

        self.run_for_param_set([content_recording_js, self.content_timeouts], extended)
        self.run_for_param_set([content_violations_js, self.collisions_timeouts], extended)

        # print("\nextended", extended)
        # print("\nzoom_list", zoom_list)

        if not extended:
            default_coll, default_esc, default_ext = self.fetch_chosen_zoom_bugs("100")

            self.organize_js_reported_bugs(zoom_list)  # firstly 100 - 200

            _ = len(default_coll) + len(default_esc) + len(default_ext)
            bugs_found_halfway = _ < len(self.collisions) + len(self.escapes) + len(self.extinctions)
            print("\nbugs_found_halfway", bugs_found_halfway)

            if bugs_found_halfway:
                return self.collect_scaling_collisions(extended=True)

        if extended:
            self.organize_js_reported_bugs(zoom_list)
            self.zoom_list = self.zoom_list + self.zoom_list_extra

        width, height = self.dims_at_zoom("100")
        self.driver.set_window_rect(width=width, height=height)
        self.driver.execute_script(cleanup_js)

    def fetch_chosen_zoom_bugs(self, zoom):
        fetch_100_pattern = f"%s.filter(bug => /{zoom}%s zoom/.test(bug.problem));"
        collisions, escapes, extinctions = [
            *map(
                lambda results: self.driver.execute_script(f"return {fetch_100_pattern % (results, '%')}"),
                ["window.collisionsResult", "window.escapesResult", "window.extinctionsResult"],
            )
        ]

        collisions, escapes, extinctions = [
            *map(
                lambda fails, name: self.order_failed_elements("100", fails, name),
                [collisions, escapes, extinctions],
                ["collisions", "escapes", "extinctions"],
            )
        ]

        return collisions, escapes, extinctions

    def ordered_collisions(self, zoom, collisions, first, second):
        return {
            _fix_numeral_selector(
                Element(bug.get("elements")[first], self.driver).get_selector()
            ): f'Collision between this element and {Element(bug.get("elements")[second], self.driver)}\
            {bug.get("problem")[32:]}'
            for bug in collisions
            if re.findall(r"\d{3}%", bug.get("problem"))[0] == f"{zoom}%"
        }

    def ordered_escapes(self, zoom, escapes):
        return {
            _fix_numeral_selector(Element(bug.get("element"), self.driver).get_selector()): bug.get("problem")
            for bug in escapes
            if re.findall(r"\d{3}%", bug.get("problem"))[0] == f"{zoom}%"
        }

    def order_failed_elements(self, zoom, failed_elements, name, mirrored=False):
        if name == "collisions":
            main_idx, idx = int(mirrored), int(not mirrored)
            _ = self.ordered_collisions(zoom, failed_elements, main_idx, idx)

            _.update(self.collisions)  # rewrite older zoom with younger one
            self.collisions = _

            if not mirrored:
                return self.order_failed_elements(zoom, failed_elements, name, mirrored=True)

            failed_elements = _
        else:
            failed_elements = self.ordered_escapes(zoom, failed_elements)

        if name == "escapes":
            failed_elements.update(self.escapes)
            self.escapes = failed_elements
        else:
            # do extinctions filter stuff (only if zoom != 100)
            failed_elements.update(self.extinctions)
            self.extinctions = failed_elements

        return failed_elements

    def organize_js_reported_bugs(self, zoom_list):
        """
        Operate all collected results from javascript part.
        Sift 100% zoom bugs, generates proper dicts for reported bugs,
        assign problem zooms, invokes report of warnings and
        postprocess lost elements without sensible alternative.
        """
        collisions = self.driver.execute_script("return window.collisionsResult;")
        escapes = self.driver.execute_script("return window.escapesResult;")
        extinctions = self.driver.execute_script("return window.extinctionsResult;")

        for zoom in zoom_list:
            self.order_failed_elements(zoom, collisions, "collisions")
            self.order_failed_elements(zoom, escapes, "escapes")
            self.order_failed_elements(zoom, extinctions, "extinctions")

        self.approve_vanished_without_alternatives()

    def wrap_failed_results(self):
        self.collisions, self.escapes, self.extinctions = [
            *map(
                lambda collection: {
                    sel: msg
                    for sel, msg in self.collisions.items()
                    if sel in self.try_locate_reported([*collection.keys()])
                },
                [
                    self.collisions,
                    self.escapes,
                    self.extinctions,
                ],
            )
        ]

        for _ in (self.collisions, self.escapes, self.extinctions):
            self.result["elements"].extend(
                [
                    *map(
                        lambda sel: {
                            "element": Element(self.driver.find_element_by_css_selector(sel), self.driver),
                            "problem": _.get(sel),
                            "error_id": message2error(_.get(sel)),
                            "severity": "FAIL",
                            "zoom": [
                                z[:-1] for z in re.findall(r"\d{3}%", _.get(sel)) if z[:-1] in self.zoom_list
                            ][0],
                        },
                        _,
                    )
                ]
            )

        self.result["elements"] = [
            bug.__setitem__(
                "interaction_sequence",
                [{"element": bug.get("element"), "action": "zoom", "zoom_percent": bug.get("zoom")}],
            )
            or bug
            for bug in self.result["elements"]
            if bug.get("zoom") != "100"
        ]

        zoom_messages = [
            zoom
            for zoom in [
                re.findall(r"\d{3}%", zoom)[0][:-1]
                for zoom in [element["problem"] for element in self.result["elements"]]
            ]
        ]
        self.result["problem_zooms"] = sorted([*set(zoom_messages)])

    def approve_vanished_without_alternatives(self):
        """
            Postprocess lost elements without sensible alternative.
            Will remain those only, who have no alternative.
        Args:
            vanished_selectors (list): Elements selectors of 'js extincted' data
            zoom_value (str): current zoom - to collect current visible elements

        Returns:
            Selectors of extincted elements without alternative.
        """
        # print("\napprove_vanished_without_alternatives")

        failed_zooms = [re.findall(r"\d{3}%", zoom)[0][:-1] for zoom in [*self.extinctions.values()]]
        failed_zooms = sorted([*set(failed_zooms) - set(["100"])])

        for zoom in failed_zooms:
            known_content = self.driver.execute_script("return window.scaleFollowedContent[arguments[0]];", zoom)
            known_content.update(self.driver.execute_script("return window.scaleFollowedContent['100'];"))
            known_content = {Element(elem, self.driver) for elem in known_content.get("functional")}

            width, height = self.dims_at_zoom(zoom)
            self.driver.set_window_rect(width=width, height=height)

            self.content_nodes_info = {
                node: info for node, info in zip(known_content, map(self._info_of_node_text, known_content))
            }

            # print("\nself.extinctions", len(self.extinctions))
            print("\nvanished zooms", zoom)
            self.extinctions = {
                ext_sel: val
                for ext_sel, val in self.extinctions.items()
                if not self.part_of_slideshow(ext_sel) and not self.has_alternative(ext_sel)
            }

    def decorative_handler_warnings(self):
        """
        Temporary worker to report 'decorative bugs' warnings.
        Purpose for QA
        """
        warnings, encountered = self.decorative_warnings, 0
        self.driver.execute_script(
            warning_escapes_js,
            warnings["escapes"],
        )
        self.driver.execute_script(
            warning_extinctions_js,
            warnings["extinctions"],
        )
        self.driver.execute_script(
            warning_collisions_js,
            warnings["collisions"],
        )

        encountered = self.driver.execute_script("return window.warningsEncountered;")
        self.result["Notes"] = f"{encountered} more collisions have been detected across the site"

        self.driver.execute_script("window.hideFixed();")
        fullpage_screenshot = Screenshot.full_page(self.driver)
        screenshot_filename = self.driver.current_url.split(".")[-2]
        screenshot_filename = f"screenshots/warnings_scaling_{screenshot_filename.replace('/', '_')}.png"
        fullpage_screenshot.save(screenshot_filename)

    def dims_at_zoom(self, zoom):
        return map(lambda size: size / int(zoom) * 100, (self.window_rect["width"], self.window_rect["height"]))

    def set_window(self, extended=False):
        """
        Generator method responsible for webpage zoom by means of window scaling by 'zoom' times
        """
        zoom_list = extended and self.zoom_list_extra or self.zoom_list
        for zoom in zoom_list:
            width, height = self.dims_at_zoom(zoom)
            yield width, height, zoom

    def _info_of_node_text(self, node: Element):
        """
        Args:
            node (Element): element to get its info
        Returns:
            set of some info of the element
        """
        node = self.driver.execute_script(self.select_js, node.get_selector())
        node_attrs = self.driver.execute_script("return window.sensibleAttrs(arguments[0])", node)
        node_attrs = [re.sub("\W+", " ", data) for data in node_attrs]
        node = Element(node, self.driver)
        node_text = node.get_text(self.driver)
        node_text = re.sub("\W+", " ", node_text).split()

        return set(node_text).union(node_attrs)

    def part_of_slideshow(self, instance_selector):
        with_slide = False
        extinct = Element(
            self.driver.execute_script(self.select_js, instance_selector),
            self.driver,
        )
        print("\nextinct", extinct)
        parent = extinct.get_parent(self.driver)
        while parent.tag_name != "body":
            print("parent", parent)
            parent_attrs = self._info_of_node_text(parent)
            parent_attrs = " ".join(re.sub(r"[-_ ]", " ", attr) for attr in [*parent_attrs])
            if any(mark in parent_attrs for mark in ["carousel", "slide", "transition"]):
                siblings = parent.find_by_xpath(f"./descendant::{extinct.tag_name}", self.driver)
                if len(siblings):
                    with_slide = True
                    print("\nWITH slide", extinct)
                    break
            parent = parent.get_parent(self.driver)

        return with_slide

    def has_alternative(self, vanished_node_selector):
        """
            Checks if vanished_node has alternative among current visible nodes
        Returns:
            bool: has alternative or has no
        """
        print("\nhas_alternative")
        vanished_node = Element(
            self.driver.execute_script(self.select_js, vanished_node_selector),
            self.driver,
        )
        print("vanished_node", vanished_node)
        content_replacement_number = 0.6
        info_cardinality = len(self._info_of_node_text(vanished_node))
        _ = any(
            len(self._info_of_node_text(vanished_node).intersection(alt_info))
            > content_replacement_number * info_cardinality
            for alt_info in {alt: info for alt, info in self.content_nodes_info.items()}.values()
        )
        print("alternative", _)

        return _

    # * dev helper *
    def save_page(self, name):
        fullpage_screenshot = Screenshot.full_page(self.driver)
        screenshot_filename = f"reports/{name}.png"
        fullpage_screenshot.save(screenshot_filename)

        with open(f"reports/{name}.html", "w") as cp_page:
            cp_page.write(self.driver.find_element_by_xpath("//html").get_attribute("outerHTML"))
