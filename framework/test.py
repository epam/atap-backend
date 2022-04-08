import logging
import threading
import sys
import time
import traceback
import uuid
import re
from types import ModuleType

from selenium import webdriver

from framework import xlsdata, activity, vpat
from framework.element_locator import DEFAULT_TARGET_ELEMENTS, ElementLocator

MIN_FRAMEWORK_VERSION = 2

STATUSES = ["READY", "RUNNING", "NOTRUN", "NOELEMENTS", "PASS", "WARN", "FAIL", "ERROR"]

WCAG_REGEX = re.compile(r"""([0-9]+\.)+[0-9]""")

logger = logging.getLogger("framework.test")

TESTDIR_NAME = "tests"


class TestMalformedException(Exception):
    pass


class Test:
    def __init__(self, test_module: ModuleType, name: str, category: str, finished_callback=None):
        self.status = "LOADING"
        self.category = category
        self.name = name[:-3]
        self.execution_time = None
        self.timing_event = None
        self.message = None
        self.depends = []
        self.problematic_elements = []
        self.checked_elements = set()
        self.result = None
        self.visible = True
        self.framework_version = 0
        # ? never used self.finished_callback = finished_callback
        self.problematic_pages = []
        test_metadata = xlsdata.get_data_for_issue(self.name)
        self.human_name = test_metadata["issue_type"]
        self.run_times = list()

        logger.info(f"==>Loading {self.name}")

        if self.human_name.startswith("#"):
            logger.warning("===>No name provided, using programmatic name")
            self.human_name = f"{self.category}/{self.name}"
            self.visible = False
        try:
            self.framework_version = test_module.framework_version
        except AttributeError:
            logger.warning("===>No framework version, assuming 0")
        if self.framework_version < MIN_FRAMEWORK_VERSION:
            logger.warning(
                f"===>Test outdated, current framework version:{MIN_FRAMEWORK_VERSION}, test supports {self.framework_version}"
            )
            self.visible = False
        if self.framework_version >= 4:
            try:
                self.elements_type = test_module.elements_type
            except AttributeError:
                self.message = "No elements_type attribute"
                self.status = "ERROR"
                raise TestMalformedException("Test missing 'elements_type' attribute")

        try:
            self.webdriver_restart_required = test_module.webdriver_restart_required
        except AttributeError:
            self.webdriver_restart_required = True
            logger.warning("===>webdriver_restart_required not defined, assuming True")

        try:
            self.test_func = test_module.test
            self.status = "READY"
            logger.info("===>OK")
        except AttributeError:
            logger.error("===>No test function!")
            self.message = "No test function"
            self.status = "ERROR"

        self.WCAG = test_metadata["WCAG"]

        if self.WCAG is not None and not WCAG_REGEX.match(self.WCAG):
            self.message = "WCAG attribute malformed"
            self.status = "ERROR"
            raise TestMalformedException("'WCAG' attribute malformed, should be period-separated numbers")

        try:
            self.test_data = test_module.test_data
        except AttributeError:
            logger.warning("===>No unit test data")
            self.test_data = None

        try:
            self.locator_required_elements = test_module.locator_required_elements
        except AttributeError:
            self.locator_required_elements = DEFAULT_TARGET_ELEMENTS

        try:
            self.depends = test_module.depends
        except AttributeError:
            pass

    def reset(self):
        self.status = "READY"
        self.problematic_elements.clear()
        self.checked_elements.clear()
        self.message = None

    def merge_other_test(self, other_test):
        if other_test.status not in STATUSES:
            logger.error(f"Invalid status for other test {other_test.name}:{other_test.status}, not merging")
            return
        if STATUSES.index(other_test.status) > STATUSES.index(self.status):
            self.status = other_test.status
        self.checked_elements.update(other_test.checked_elements)

        for element in other_test.problematic_elements:
            for existing_element in self.problematic_elements:
                if element["element"] == existing_element["element"]:
                    for page in element["pages"]:
                        if page not in existing_element["pages"]:
                            existing_element["pages"].append(page)
                    break
            else:
                self.problematic_elements.append(element)

        for problematic_page in other_test.problematic_pages:
            self.problematic_pages.append(problematic_page)

        self.run_times.extend(other_test.run_times)

    def set_interval(self, worker, *args, seconds=1):
        def interval_loop():
            while not self.timing_event.wait(seconds):
                worker(*args)

        thread = threading.Thread(target=interval_loop)

        thread.daemon = True
        thread.start()

    def update_execution_time(self, start_time):
        """During test run
        Calculate difference between the test start time and current time
        Update execution_time of test

        Args:
            start_time (int): test start execution timestamp
        """
        self.execution_time = round(time.time() - start_time)

    def run(
        self,
        webdriver_instance: webdriver.Firefox,
        activity: activity.Activity,
        element_locator: ElementLocator,
        dependencies=None,
    ) -> str:
        if self.status == "ERROR":
            logger.error(f"==>Cannot run {self.category}/{self.name}, not loaded properly")
            return self.status
        test_logger = logging.getLogger(f"framework.tests.{self.name}")
        test_logger.info(f"==>Running '{self.human_name}'")
        self.status = "RUNNING"
        test_logger.info("===>START")
        try:
            self.timing_event = threading.Event()
            start_time = time.time()

            self.set_interval(self.update_execution_time, start_time)
            if dependencies is None:
                result = self.test_func(
                    webdriver_instance=webdriver_instance, activity=activity, element_locator=element_locator
                )
            else:
                result = self.test_func(
                    webdriver_instance=webdriver_instance,
                    activity=activity,
                    element_locator=element_locator,
                    dependencies=dependencies,
                )
            self.result = result
        except Exception as e:
            test_logger.error("===>Exception during test execution:")
            traceback.print_exc(file=sys.stdout)
            self.status = "ERROR"
            self.message = f"Exception during text execution:{e}"
            self.problematic_pages.append(f"{activity.url} ({activity.name})")

            self.timing_event.set()

            return self.status
        try:
            if result["status"] in STATUSES:
                if STATUSES.index(result["status"]) > STATUSES.index(self.status):
                    self.status = result["status"]
                    self.message = result["message"] if "message" in result else "---no message---"
                test_logger.info(f"===>{self.status}:{self.message}")
                if "elements" in result:
                    for element in result["elements"]:
                        for existing_element in self.problematic_elements:
                            if (
                                "element" in element
                                and element["element"] == existing_element["element"]
                                or "element" not in element
                                and element["source"] == existing_element["source"]
                            ):
                                break
                        else:
                            self.problematic_elements.append(element)

                if self.framework_version >= 3 and "checked_elements" not in result:
                    self.status = "ERROR"
                    self.message = "No 'checked_elements' in result dict'"
                    test_logger.error("===>No 'checked_elements' in result dict")
                    return self.status
                if self.framework_version >= 3:
                    self.checked_elements.update(result["checked_elements"])
            else:
                self.status = "ERROR"
                self.message = f"Invalid status:'{result['status']}'"
                test_logger.error(f"===>Invalid status '{result['status']}'", end="")

            important_examples = 0
            max_important_examples = 5

            for problematic_element in self.problematic_elements:
                if "element" not in problematic_element:
                    test_logger.error("===>Problematic element missing 'element' entry")
                    self.status = "ERROR"
                    self.message = "===>Problematic element missing 'element' entry"
                    return self.status
                if "pages" not in problematic_element:
                    problematic_element["pages"] = []
                problematic_element["pages"].append(activity.url)
                if "error_id" not in problematic_element:
                    problematic_element["error_id"] = self.name
                if self.framework_version >= 6 and "severity" not in problematic_element:
                    test_logger.error("===>Problematic element missing severity (FAIL/WARN)")
                    self.status = "ERROR"
                    self.message = "Problematic element missing severity (FAIL/WARN)"
                    problematic_element["severity"] = "ERROR"
                    return self.status
                if "problem" not in problematic_element:
                    if self.WCAG is None:
                        test_logger.error("===>Element missing 'problem' attribute, test has no 'WCAG' attribute")
                        self.status = "ERROR"
                        self.message = "Element missing 'problem' attribute, test has no 'WCAG' attribute"
                        problematic_element["problem"] = "ERROR"
                        return self.status
                    problematic_element["problem"] = vpat.map_error_id(self.WCAG, problematic_element["error_id"])
                if "severity" in problematic_element:
                    if problematic_element["severity"] not in ("FAIL", "WARN"):
                        test_logger.error(f"===>Invalid severity '{problematic_element['severity']}'")
                        self.status = "ERROR"
                        self.message = f"Invalid severity '{problematic_element['severity']}'"
                        return self.status
                else:
                    problematic_element["severity"] = "FAIL"
                if important_examples < max_important_examples:
                    important_examples += 1
                    problematic_element["important_example"] = True
                else:
                    problematic_element["important_example"] = False
                problematic_element["uuid"] = uuid.uuid4().hex
        except TypeError:
            test_logger.error("===>Test function did not return a dict")
            self.status = "ERROR"
            self.message = "Test function did not return a dict"
        finally:
            self.timing_event.set()

        test_logger.info(f"===>OK, took {self.execution_time}s on {activity.name} ({activity.url})")

        self.run_times.append((activity.url, activity.name, self.execution_time))

        return self.status
