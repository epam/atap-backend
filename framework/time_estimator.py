import time
import logging
import json
from datetime import date

import numpy as np
from scipy.stats import levy
from selenium import webdriver

from framework.await_page_load import wait_for_page_load
from framework.test_system import load_tests_with_dependencies

from web_interface.apps.page.models import Page
from web_interface.apps.activity.models import Activity
from web_interface.api.framework_data import service
from web_interface.apps.task.task_functional import estimate_time

logger = logging.getLogger("framework.time_estimator")

ELEMENTS_TO_COUNT = ["a", "img", "button", "input", "form", "table", "div", "span"]

RANDOM_PAGE_ELEMENT_JS = """
    const randomIndex = Math.floor(Math.random() * arguments[0].length);

    return arguments[0][randomIndex];
"""


def get_page_size(url):
    webdriver_instance, page_load_time = _start_driver_measure_load_time(url)

    results = {"page_load_time": page_load_time}
    logger.info("Counting all elements...")
    results["all_elements_count"] = len(webdriver_instance.find_elements_by_xpath("//*"))

    for element_type in ELEMENTS_TO_COUNT:
        logger.info(f"Counting {element_type} elements...")
        results[element_type] = len(webdriver_instance.find_elements_by_xpath(f"//{element_type}"))

    logger.info("DONE")
    webdriver_instance.quit()

    return results


def get_page_size_data(page: Page):
    if page.page_size_data is None:
        logging.error("Page_size_data is None")
        page.page_size_data = json.dumps(get_page_size(page.url))
        page.save()

    page_size_data = json.loads(page.page_size_data)

    page_size_data["name"] = page.name
    page_size_data["url"] = page.url
    page_size_data["activity_count"] = Activity.objects.filter(page=page).count()

    if page_size_data["activity_count"] == 0:
        page_size_data["activity_count"] = 1

    return page_size_data


class TestingSimulator:
    def __init__(self, tests_to_run, pages_with_size_data, thread_num=4):
        self.test_names_to_run = tests_to_run
        self.pages_with_size_data = pages_with_size_data
        self.threads = [None] * thread_num
        self.simulation_time = 0
        self.test_queue = []
        self.start_time = 0.0  # TODO design start_time; around 0 value makes no sense
        self.finished_tests = []
        self.url_list = []
        self.page_activities = []
        self.page_names = []
        self.test_dependencies = []
        self.disclosed_test_names = []
        self.test_regression_model_data = []
        self.screenshot_amount_gen = None
        self.estimated_test_times_of_pages_collection = {}
        self.first_test_name = ""

    def simulate_testing(self):
        self.start_time = time.time()
        logger.info("Simulate testing")
        logger.info("Loading test data...")
        self.__set_pages_vars()
        self.__set_tests_vars()

        self.screenshot_amount_gen = _test_screenshot_amount_choice_from_levy_distribution()
        self.estimated_test_times_of_pages_collection = self.__set_time_estimates_sequence()
        self.__simulate_test_queue()

        logger.info("Finished time estimates of test data")
        logger.info("Updating threads with tests...")
        self.__update_threads_with_tests()

        self._finish_thread_simulation()

        estimated_thread_times = dict.fromkeys(range(len(self.threads)), 0)
        for time_data in self.finished_tests:
            estimated_thread_times[time_data.get("thread_id")] += time_data.get("simulated_time")

        # * actually testing with single thread, so get straight sum instead of max
        # * so add whole task start_time
        self.simulation_time = round(sum(estimated_thread_times.values()) + time.time() - self.start_time)
        logger.info(f"Simulation time estimates {self.simulation_time}s")

    def _finish_thread_simulation(self):
        min_advance_time = 172800  # * 2 days limit
        visited_pages = set()
        for thread_id, thread_test in enumerate(self.threads):
            time_locator_appendage = 0
            if thread_test is not None:
                visited_page_name = thread_test["locator"]["name"].split("locator_")[1]
                if visited_page_name not in visited_pages:
                    time_locator_appendage = thread_test["locator"]["time"]
                    visited_pages.add(visited_page_name)

                thread_test["simulated_time"] = min(
                    min_advance_time,
                    time_locator_appendage
                    + sum(thread_test[test_name]["time"] for test_name in ["test", "screenshot"]),
                )

                logger.info(f"Finished {thread_test['test']} simulation")
                self.finished_tests.append({"thread_id": thread_id, **thread_test})
        logger.info(
            f"Finished simulating for {len(self.finished_tests)} tests with {len([*filter(None, self.threads)])} threads.\nTook {time.time() - self.start_time:.3f}s"
        )

    def __simulate_test_queue(self):
        for page_name, page_activity_amount in zip(self.page_names, self.page_activities):
            for activity_id in range(page_activity_amount):
                activity_run_times = next(self.estimated_test_times_of_pages_collection)

                locator_time, test_times, screenshot_times = [
                    activity_run_times[key] for key in ("locator", "test", "screenshot")
                ]

                for test_name, test_time, ss_time in zip(
                    self.disclosed_test_names,
                    test_times,
                    screenshot_times,
                ):
                    # * None depends for aXe
                    dep = _is_not_axe_test_name(test_name) and [*self.test_dependencies].pop(0) or None
                    self.test_queue.append(
                        {
                            "locator": {
                                "name": f"locator_{page_name}",
                                "time": locator_time,
                            },
                            "test": {
                                "name": f"{test_name}_page_{page_name}_activity_{activity_id}",
                                "time": test_time,
                                "depends": dep and [f"{d}_{page_name}_{activity_id}" for d in dep],
                            },
                            "screenshot": {
                                "name": f"screenshots_{test_name}",
                                "time": ss_time,
                            },
                        }
                    )

    def prepare_page_data_for_time_estimator_model(self):
        """
        Returns: list of dicts: modified page data for time prediction
        """
        logger.info("Handling page data for regression time estimate")

        features_for_estimate = service.database_columns
        data_for_estimate = [
            {
                "activity_count": activity_count,
                "page_name": page_name,
                "test_names": self.disclosed_test_names,
                "test_data": dict.fromkeys(features_for_estimate, 0),
            }
            for activity_count, page_name, url in zip(
                [data["activity_count"] for data in self.pages_with_size_data],
                self.page_names,
                self.url_list,
            )
        ]

        for n, test_data_of_page in enumerate(self.pages_with_size_data):
            test_data_of_page["date_was_run_y_m_d"] = date.today().strftime("%y-%m-%d")
            # * drop temporary
            del test_data_of_page["url"]
            del test_data_of_page["activity_count"]
            # * single page may have many activities and tests
            for _ in self.disclosed_test_names:
                # * maintain order for dataframe
                test_data_of_page = {
                    "name": None,
                    "date_was_run_y_m_d": test_data_of_page["date_was_run_y_m_d"],
                    **test_data_of_page,
                }
                # * to replace name with current test name when estimate
                assert sum([*test_data_of_page.keys()].count(f) for f in features_for_estimate) == len(
                    features_for_estimate
                ), "Wrong amount of features"

            data_for_estimate[n]["test_data"] = test_data_of_page

        return data_for_estimate

    def __set_tests_vars(self):
        framework_tests_with_dependencies = []
        # * aXe test is dict with testing rule, e.t.c, so take names only
        for test_name in self.test_names_to_run:
            if _is_not_axe_test_name(test_name):  # * framework test
                test_with_dependencies = load_tests_with_dependencies([test_name], None)
                framework_tests_with_dependencies.extend(test_with_dependencies)
                self.disclosed_test_names.extend([test.name for test in test_with_dependencies])
            else:  # * aXe test
                self.disclosed_test_names.append(test_name)

        # * aXe has no dependencies
        self.test_dependencies = [test_data.depends for test_data in framework_tests_with_dependencies]

        self.test_regression_model_data = self.prepare_page_data_for_time_estimator_model()

    def __total_test_screenshotting_time(self):
        """
        Formula approach: page_load_time + element_count * (screenshotting_time + (optional interact): page_load_time)
        Neglect single page_load_time, take optional as permanent,
        because of element_count randomness

        Returns:
            int: proposed time for some test screenshot task
        """
        element_count = next(self.screenshot_amount_gen)
        screenshot_with_page_load_time = _random_element_screenshotting_time()

        # * at least 10s for zero screenshots
        return 10 + round(element_count * screenshot_with_page_load_time)

    def __set_time_estimates_sequence(self):
        for page_tests_data in self.test_regression_model_data:
            test_names, test_data_for_model = [page_tests_data[key] for key in ["test_names", "test_data"]]
            test_stats_dataframe = estimate_time.db_run_times_dataframe()

            test_time_seq, screenshot_time_seq = [], []
            locator_time = _total_page_locating_time()
            for test_name in test_names:
                if _is_not_axe_test_name(test_name):
                    # * specify test_name along with page_data
                    test_data_for_model.update({"name": test_name})
                    test_time = _estimated_time_for_test_data(test_data_for_model, test_stats_dataframe)
                    screenshot_estimate_for_test = self.__total_test_screenshotting_time()

                    test_time_seq.append(test_time)
                    screenshot_time_seq.append(screenshot_estimate_for_test)
                else:
                    # * constant guess for aXe
                    test_time_seq.append(5)
                    screenshot_time_seq.append(5)

            yield dict(locator=locator_time, test=test_time_seq, screenshot=screenshot_time_seq)

    def __set_pages_vars(self):
        [
            (
                self.page_activities.append(page["activity_count"]),
                self.url_list.append(page["url"]),
                self.page_names.append(page["name"]),
            )
            for page in self.pages_with_size_data
        ]

    def __get_next_queued(self):
        self.first_test_name = None

        while len(self.test_queue):
            test_queue_timings = self.test_queue.pop(0)
            test_timing_data = test_queue_timings["test"]
            if self.first_test_name is None:
                self.first_test_name = test_timing_data["name"]
            elif test_timing_data["name"] == self.first_test_name:
                # * reached the start point
                if not len(self.test_queue):
                    return test_queue_timings
                # * still got tests without dependencies
                # * assign first test first until []
                self.first_test_name = self.test_queue[0]

                return test_queue_timings

            # * quit: get next aXe
            if test_timing_data["depends"] is None:
                return test_queue_timings
            for dependency in test_timing_data["depends"]:
                # * add dependency to run
                if dependency not in self.finished_tests:
                    self.test_queue.append(test_queue_timings)
                    break
            else:
                # * quit: get next
                return test_queue_timings

        # * quit: empty queue
        return None

    def __update_threads_with_tests(self):
        for thread_id in range(len(self.threads)):
            # * thread is idle
            if self.threads[thread_id] is None:
                testing_task = self.__get_next_queued()
                # * add and start mock testing
                if testing_task is not None:
                    logger.info(
                        f"Thread {thread_id} picked up {testing_task['test']['name']} for {testing_task['test']['time']}s test time"
                    )
                    testing_task["start_time"] = time.time() - self.start_time
                    self.threads[thread_id] = testing_task
                else:
                    logging.info(f"No more tests for thread {thread_id}")
                    break


def _start_driver_measure_load_time(url):
    webdriver_instance = webdriver.Firefox()
    logger.info(f"Opening {url}")
    webdriver_instance.get(url)
    logger.info("Waiting for the page to fully load...")

    load_page_start = time.time()
    wait_for_page_load(webdriver_instance)
    page_load_time = time.time() - load_page_start

    return webdriver_instance, page_load_time


def _estimated_time_for_test_data(test_data: dict, dataframe) -> int:
    test_name = test_data["name"]

    # * disable accurate estimator at job start
    return estimate_time.get_test_mean_time(test_name, dataframe)


def _total_page_locating_time():
    # * hard code average locator time
    return 14


def _test_screenshot_amount_choice_from_levy_distribution(n_points: int = 5):
    """
    Randomize screenshot amount for test. Cannot predict in advance.
    Take probability distribution, close to real values.

    Args:
        n_points: Maximum number of screenshots for test. Defaults to 5, should be global for ATAP.

    Yields:
        int: Guessed number of screenshots: 0 to 5
    """
    levy_dist = np.round(levy.pdf(np.linspace(0, n_points, n_points), -0.5, 1.8), 5)
    # * normalize
    levy_dist /= np.sum(levy_dist)
    independent_uniform_dist = np.linspace(0, n_points, n_points)

    while True:
        yield np.round(np.random.choice(independent_uniform_dist, size=1, p=levy_dist)).astype("int32")[0]


def _random_element_screenshotting_time():
    # * hard code average single screenshot time
    return 8


def _is_not_axe_test_name(name):
    return name.startswith("test")
