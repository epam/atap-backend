import json
from random import random, gauss
from pandas.core.computation.ops import UndefinedVariableError
from typing import List, Tuple, Generator

from selenium.common.exceptions import WebDriverException

from django.http import HttpResponse

from framework import time_estimator
from framework.test_system import discover_tests, load_tests_with_dependencies

from web_interface.apps.job.models import Job
from web_interface.apps.page.models import Page
from web_interface.apps.framework_data.models import TestTiming
from web_interface.api.framework_data.estimate_model_helpers.load_dataframe import get_clear_tests_dataframe
from web_interface.api.job.job_services import download_timings_db


def calculate_job_tests_pages_and_its_timings(job=None, job_id=None):
    # * get last saved job if no id provided
    if job_id:
        job = Job.objects.get(id=job_id)

    job_pages, test_names = _get_job_pages_and_test_names(job)
    page_elements_data = [time_estimator.get_page_size_data(page) for page in job_pages]

    # ! 4 to account dependencies
    thread_num = len(test_names) * len(job_pages) * 4
    simulator = time_estimator.TestingSimulator(test_names, page_elements_data, thread_num=thread_num)
    simulator.simulate_testing()
    simulated_test_timings = simulator.finished_tests

    return simulator.simulation_time, job_pages, test_names, simulated_test_timings


# * best guess 'calculate time'
def calculated_job_runtime(job_pages, job_tests) -> int:
    job_pages_number = len(job_pages)
    job_test_runs_dataframe = db_run_times_dataframe()
    job_mean_test_times = _dataframe_mean_times(job_test_runs_dataframe, job_tests)

    total_testing_time = job_pages_number * sum(job_mean_test_times)

    page_locating_time, element_mean_screenshotting_time = 14, 12
    total_page_locating_time, total_screenshotting_time = (
        job_pages_number * page_locating_time,
        job_pages_number * len(job_mean_test_times) * element_mean_screenshotting_time,
    )

    return total_page_locating_time + total_testing_time + total_screenshotting_time


def db_run_times_dataframe():
    timings_data = download_timings_db(TestTiming.objects.all())
    resp = HttpResponse(timings_data, content_type="text/csv")

    return get_clear_tests_dataframe(resp.content)


# * accurate 'calculate time'
def estimated_job_execution_time(
    job_pages: List[int], job_tests: List[str], time_for_cache_to_restart: int = 25
) -> int:
    pages = Page.objects.filter(id__in=job_pages)

    page_data = [time_estimator.get_page_size_data(page) for page in pages]
    thread_num = len(job_tests) * len(pages) * 4

    simulator = time_estimator.TestingSimulator(job_tests, page_data, thread_num=thread_num)
    try:
        simulator.simulate_testing()
    except WebDriverException:  # * network exception, return something
        return 300
    estimated_testing_time_total = simulator.simulation_time

    return estimated_testing_time_total + time_for_cache_to_restart


def get_test_mean_time(test_name, dataframe) -> int:
    # * query run_times from dataframe features
    try:
        requested_test_frame = dataframe.query("name == @test_name")
        assert not requested_test_frame.empty
    except (AssertionError, UndefinedVariableError):
        # * UndefinedVariableError - special for web test pass
        print(f"WARNING: no run time stats for test {test_name}")
        # * nearly pointless for missing test data
        try:
            mean_time = _get_hardcoded_generalized_time(dataframe.run_times, test_name)
        except AttributeError:
            # * special for web test pass
            mean_time = 180
    else:
        mean_time = _get_confidence_median_time_of_test(requested_test_frame.run_times)

    return mean_time


def task_accepting_order_estimated_runtimes(pages_to_run, job_test_list, simulated_test_timings) -> Generator:
    task_timings_data = []
    tests_to_run_list = _get_run_ordered_test_names(job_test_list, len(pages_to_run))

    # * discover_tests(tests_to_run_list) -> fail loading for every page
    tests_to_run = [
        discover_tests([queued_test_name], filter_category=None)[0]
        if queued_test_name.startswith("test")
        else _temp_axe_test_object(queued_test_name)
        for queued_test_name in tests_to_run_list
    ]

    pages_to_run_times, tests_to_run_times, screenshots_to_run_times = _get_task_estimate_mappings(
        pages_to_run, tests_to_run
    )

    _build_list_of_tasks_ordered_for_job_run(
        simulated_test_timings, tests_to_run, pages_to_run_times, tests_to_run_times, screenshots_to_run_times
    )

    # * complete task_timings_data in order, regrouping locator and screenshot
    _append_locator_task_estimates_for_pages(pages_to_run, pages_to_run_times, task_timings_data)
    _append_test_task_estimates(tests_to_run_times, task_timings_data)
    _append_screenshot_task_estimates_for_test_of_pages(screenshots_to_run_times, task_timings_data)

    yield  # * build task_timings_data and quit, waiting for first task run
    running_task_name = yield  # * send init value

    for current_tasks_data in task_timings_data:
        # * testing queue is shuffled for some reason
        # * aXe order is: test -> locator -> screenshot
        if current_tasks_data["task_name"] != running_task_name:
            for tasks_data in task_timings_data:
                if tasks_data["task_name"] == running_task_name:
                    current_tasks_data = tasks_data
                    break
            # * disable until model task is fixed
            # else:  # * no data for running task
            # assert False, f"Task timing queue is broken for {running_task_name}\n"
            # "This message could be throwed because of another exception. Try to find first traceback message"

        running_task_name = yield current_tasks_data  # * update running_task_name, yield


def update_job_test_time_func(job_id):
    job = Job.objects.get(id=job_id)

    job_pages, test_names = _get_job_pages_and_test_names(job)
    job.estimated_testing_time = calculated_job_runtime(job_pages, test_names)

    job.save()


def update_page_size_func(page_id) -> None:
    page = Page.objects.get(id=page_id)
    page_size_info = time_estimator.get_page_size(page.url)

    page.page_size_data = json.dumps(page_size_info)
    page.save()


def _get_confidence_median_time_of_test(test_run_times) -> int:
    plus_minus_one = 1 if random() < 0.5 else -1
    random_percentile = round(0.5 + plus_minus_one * gauss(0.25, 0.07) / 2, 3)

    return round(test_run_times.quantile(random_percentile))


def _get_hardcoded_generalized_time(total_run_times, test_name) -> int:
    if test_name.startswith("test"):
        default_time = 30
        return max(round(total_run_times.median()), default_time)
    else:
        # * expect axe tests to be fast
        return 5


def _task_mean_test_time_generator(dataframe, test_list) -> Generator:
    for test_name in test_list:
        yield get_test_mean_time(test_name, dataframe)


def _dataframe_mean_times(tests_run_times_dataframe, upcoming_job_test_list) -> Tuple:
    return tuple(_task_mean_test_time_generator(tests_run_times_dataframe, upcoming_job_test_list))


def _get_dict_for_task_estimation(time, task_name, task_type):
    return dict(
        time=time,
        task_name=task_name,
        task_type=task_type,
    )


def _get_run_ordered_test_names(job_test_list, pages_amount):
    test_names = []
    # * aXe test is dict with testing rule, e.t.c, so take names only
    for test_name in job_test_list:
        if test_name.startswith("test"):  # * framework test
            test_with_dependencies = load_tests_with_dependencies([test_name], filter_category=None)
            test_names.extend([test.name for test in test_with_dependencies])
        else:  # * aXe test
            test_names.append(test_name)

    # * sort by order dependencies, tests
    return sorted(test_names * pages_amount, key=test_names.index, reverse=True)


def _temp_axe_test_object(name):
    return type("aXeTest", (object,), dict(name=name))()


def _get_task_estimate_mappings(pages, tests):
    return [
        dict.fromkeys([page.name for page in pages], 0),
        dict.fromkeys(tests, 0),
        dict.fromkeys(reversed([test.name for test in tests]), 0),
    ]


def _add_locator_estimate(estimate, task_data, pages_to_run_times):
    page_name = task_data["name"].split("locator_")[1]
    pages_to_run_times[page_name] = estimate


def _add_screenshot_estimate(estimate, test, screenshots_to_run_times):
    test.estimated_screenshooting_time = estimate
    screenshots_to_run_times[test.name] += estimate


def _add_test_estimate(estimate, test, test_name, tests_to_run_times):
    test.estimated_testing_time = tests_to_run_times[test] = estimate
    # * change dict test key to its full_name
    tests_to_run_times[test_name] = tests_to_run_times.pop(test)


def _append_locator_task_estimates_for_pages(pages, locator_times, task_timings_data):
    for page, locator_time in zip(pages, locator_times.values()):
        page.estimated_locating_time = locator_time

        # if locator_time:  # * null fox aXe
        task_timings_data.append(
            _get_dict_for_task_estimation(locator_time, f"locator_{page.name}_Main Activity", "locator")
        )


def _append_test_task_estimates(test_times, task_timings_data):
    for full_test_name, test_time in test_times.items():
        # {test}_page_{page}_activity_{activity}
        _ = full_test_name.split("_page_")
        test_name, page_name = _[0], _[1].split("_activity")[0]

        testing_task_name = f"{page_name}_Main Activity"
        testing_task_name = (
            f"{testing_task_name}_{test_name}" if test_name.startswith("test") else f"{testing_task_name}_aXe"
        )
        task_timings_data.append(_get_dict_for_task_estimation(test_time, testing_task_name, "test"))


def _append_screenshot_task_estimates_for_test_of_pages(screenshot_times, task_timings_data):
    for test_name, screenshot_time in screenshot_times.items():
        screenshoting_task_name = "screenshots"
        screenshoting_task_name = (
            f"{screenshoting_task_name}_{test_name}"
            if test_name.startswith("test")
            else f"{screenshoting_task_name}_aXe"
        )
        task_timings_data.append(
            _get_dict_for_task_estimation(screenshot_time, screenshoting_task_name, "screenshot")
        )


def _build_list_of_tasks_ordered_for_job_run(timings, tests, pages_times, tests_times, screenshots_times):
    for task_type in ["locator", "test", "screenshot"]:
        for test_time_data, test in zip(timings, tests):
            task_data = test_time_data.get(task_type)
            task_estimate = int(task_data["time"])

            if task_type == "locator":
                _add_locator_estimate(task_estimate, task_data, pages_times)
            elif task_type == "test":
                _add_test_estimate(task_estimate, test, task_data["name"], tests_times)
            else:  # * task_type == "screenshot"
                _add_screenshot_estimate(task_estimate, test, screenshots_times)


def _get_job_pages_and_test_names(job) -> Tuple[Page, str]:
    test_names, job_pages = (
        job.test_list.split(","),
        job.pages.all(),
    )

    # * FILO for some reason, see _accept_last_task
    job_pages = [*job_pages][::-1]

    return job_pages, test_names
