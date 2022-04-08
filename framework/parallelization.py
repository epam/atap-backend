import ctypes
import logging
import sys
import threading
import time
import traceback
from queue import PriorityQueue
from typing import List, Union, Optional, Tuple, Callable

import cv2 as cv
from PIL.Image import Image
from selenium import webdriver

from framework import model_wrapper, axe_integration
from framework.axe_integration import ImportedTest
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.screenshot.screenshot import Screenshot
from framework.activity import Activity
from framework.webdriver_manager import WebdriverManager

logger = logging.getLogger("framework.parallelization")


def verify_progress(func):
    def in_progress(progress_report_callback, *args, **kwargs):
        if progress_report_callback is not None:
            return func(progress_report_callback, *args, **kwargs)

    return in_progress


@verify_progress
def _start_webdriver_progress(progress_report_callback, thread_id):
    progress_report_callback(
        {
            "thread_status": {
                thread_id: "Starting webdriver...",
            }
        }
    )


@verify_progress
def _running_tasks_progress(progress_report_callback, tasks_amount: int):
    progress_report_callback({"tasks_count": tasks_amount, "overall_progress": "Running parallel tasks"})


@verify_progress
def _dependencies_waiting_progress(progress_report_callback, thread_id):
    progress_report_callback({"thread_status": {thread_id: "IDLE: Waiting for dependencies to resolve"}})


@verify_progress
def _thread_idle_progress(progress_report_callback, thread_id):
    progress_report_callback({"thread_status": {thread_id: "IDLE: No more work"}})


@verify_progress
def _unload_models_progress(progress_report_callback):
    progress_report_callback(
        {
            "overall_progress": "Unloading models",
            "thread_status": {i: "Parallel tasks finished" for i in range(16)},  # ? 16 number
        }
    )


@verify_progress
def _running_progress(progress_report_callback, thread_id, task_obj):
    progress_report_callback(
        {
            "thread_status": {
                thread_id: f"Running {task_obj.name}",
            },
            "thread_task_cancellable": {
                thread_id: task_obj.test_name is not None and task_obj.test_name != "aXe",
            },
            "thread_test_name": {
                thread_id: task_obj.test_name,
            },
            "running_task_completed": {
                thread_id: 0,
            },
        }
    )


@verify_progress
def _cancelling_task_progress(progress_report_callback, test_name, thread_id):
    progress_report_callback(
        {
            "thread_status": {
                thread_id: f"Cancelling {test_name}",
            },
            "thread_task_cancellable": {
                thread_id: False,
            },
        }
    )


@verify_progress
def _cancelled_progress(progress_report_callback, thread_id):
    progress_report_callback(
        {
            "thread_task_cancellable": {
                thread_id: False,
            },
            "thread_test_name": {
                thread_id: None,
            },
        }
    )


class NoTasksLeftException(Exception):
    pass


class TestQueue:
    def __init__(
            self,
            tasks: List[Tuple[int, 'ParallelTask']],
            tests: dict,
            axe_tasks: List['ParallelTask'],
            activities: List[Activity],
            cancelled_tests, do_interim_results: bool = False
    ):
        self.task_queue = PriorityQueue()
        self.__verify_dependencies(tasks)
        for task in tasks:
            self.task_queue.put(task)
        self.tests = tests
        self.axe_tasks = axe_tasks
        self.tests_values_fixed_order = None
        self.do_interim_results = do_interim_results
        self.activities = activities
        self.completed_tasks: List['ParallelTask'] = []
        self.running_tasks: List['ParallelTask'] = []
        self.lock = threading.RLock()
        self.unsuitable_tasks: List[Tuple[int, 'ParallelTask']] = []
        self.dependency_failed = False
        self.cancelled_tests = cancelled_tests
        self.finished_tests = {}
        self.screenshotted_tests = []

    @verify_progress
    def __complete_axe_task(self, progress_report_callback):
        for axe_test in self.finished_tests["aXe"]:
            progress_report_callback({"screenshots_for_test": axe_test})

    @verify_progress
    def __finished_screenshotting_progress(self, progress_report_callback, test_name):

        for element in self.finished_tests[test_name].problematic_elements:
            print(f"{element['element'].source} - {'screenshot' in element}")
        progress_report_callback({"screenshots_for_test": self.finished_tests[test_name]})
        self.screenshotted_tests.append(self.finished_tests[test_name])

    @verify_progress
    def __interim_progress(self, progress_report_callback, test):
        progress_report_callback({"interim_test_result": test})

    @verify_progress
    def __complete_task_progress(self, progress_report_callback):
        progress_report_callback({"tasks_complete": len(self.completed_tasks)})

    def __complete_screenshotted_or_axe(self, task, test_runner):
        if task.test_name == "aXe":
            self.__complete_axe_task(test_runner.progress_report_callback)
        elif self.finished_tests[task.test_name] not in self.screenshotted_tests:
            self.__finished_screenshotting_progress(test_runner.progress_report_callback, task.test_name)

    def __get_unfinished_test_tasks(self, task: 'ParallelTask'):
        tasks_in_queue = [x[1] for x in self.task_queue.queue]

        return [
            t
            for t in tasks_in_queue + self.running_tasks
            if t.test_name == task.test_name and not t.name.startswith("screenshot")
        ]

    def __handle_unfinished(self, task: 'ParallelTask'):
        unfinished_tasks_of_type = self.__get_unfinished_test_tasks(task)

        if unfinished_tasks_of_type:
            print(f"Task {task.name} finished, but {len(unfinished_tasks_of_type)} tasks of type remain")

    def __merge_axe_pseudo_tests(self, axe_task: 'ParallelTask', pseudo_tests) -> None:
        for axe_test in axe_task.result:
            for pseudo_test in pseudo_tests:
                if pseudo_test.name == axe_test.name:
                    pseudo_test.merge_other_test(axe_test)
                    break
            else:
                pseudo_tests.append(axe_test)

    def __complete_axe_tests(self, test_runner: 'TestRunner') -> None:
        pseudo_tests = []

        for axe_task in self.axe_tasks:
            logger.info("AXE TASK " + axe_task.name)
            if axe_task.result is not None:
                self.__merge_axe_pseudo_tests(axe_task, pseudo_tests)

        for pseudo_test in pseudo_tests:
            self.__interim_progress(test_runner.progress_report_callback, pseudo_test)
            self.finished_tests[pseudo_test.name] = pseudo_test

    def __merge_regular_test(self, finished_test):
        for activity_tests in self.tests_values_fixed_order[1:]:
            for secondary_test in activity_tests:
                if finished_test.name == secondary_test.name:
                    finished_test.merge_other_test(secondary_test)

        return finished_test

    def __complete_test_task(self, task: 'ParallelTask', test_runner: 'TestRunner'):
        self.tests_values_fixed_order = list(self.tests.values())

        for test in self.tests_values_fixed_order[0]:
            if test.name == task.test_name:
                merged_finished_test = self.__merge_regular_test(test)
                break
        else:
            raise ValueError(f"Could not find {task.test_name} in test list")

        self.finished_tests[merged_finished_test.name] = merged_finished_test
        self.__interim_progress(test_runner.progress_report_callback, merged_finished_test)

    def complete_task(self, task: 'ParallelTask', runner: 'TestRunner') -> None:
        with self.lock:
            self.running_tasks.remove(task)

            is_regular_test_task = (
                    task.test_name is not None and not task.name.startswith("screenshot") and self.do_interim_results
            )
            if is_regular_test_task:
                self.__handle_unfinished(task)

                if task.test_name == "aXe":
                    print("Submitting axe interim results")
                    self.__complete_axe_tests(runner)
                else:
                    print(f"Submitting interim results for {task.test_name}")
                    self.__complete_test_task(task, runner)
            elif task.name.startswith("screenshot"):
                self.__complete_screenshotted_or_axe(task, runner)

            self.completed_tasks.append(task)
            self.__complete_task_progress(runner.progress_report_callback)

    def __get_next_in_queue(self) -> Optional['ParallelTask']:
        if self.task_queue.empty():
            return None

        task = self.task_queue.get()
        self.unsuitable_tasks.append(task)
        return task[1]

    def _accept_last_task(self) -> None:
        accepted_task = self.unsuitable_tasks.pop(-1)
        logger.info(f"Accepted task {accepted_task[1].name} with priority {accepted_task[0]}")
        self.running_tasks.append(accepted_task[1])
        self._restore_unsuitable_tasks()

    def _restore_unsuitable_tasks(self) -> None:
        for task in self.unsuitable_tasks:
            self.task_queue.put(task)
        self.unsuitable_tasks.clear()

    @staticmethod
    def __verify_dependencies(task_list: List[Tuple[int, 'ParallelTask']]) -> None:
        task_names = [other_task[1].name for other_task in task_list]
        for task in task_list:
            deps = task[1].depends
            for dep in deps:
                if type(dep) is tuple:
                    dep = dep[0]
                if dep not in task_names:
                    raise ValueError(f"DEPENDENCY ERROR: Task {task[1].name} has an unmet dependency {dep}")

    def __secure_counts(self, counter: int, max_tries: int = 10000) -> None:
        if counter <= max_tries:
            return

        logger.fatal("pop_task is in an endless loop!")
        while not self.task_queue.empty():
            task = self.task_queue.get()[1]
            logger.fatal(f"{task.name} - {task.depends} ")

        raise ValueError("pop_task is in an endless loop!")

    def __put_dep_unsuitable_tasks(self, test_runner: 'TestRunner') -> None:
        if len(self.unsuitable_tasks) == 0:
            _thread_idle_progress(test_runner.progress_report_callback, test_runner.thread_id)
            raise NoTasksLeftException
        else:
            _dependencies_waiting_progress(test_runner.progress_report_callback, test_runner.thread_id)
            self._restore_unsuitable_tasks()

    def __skip_cancelled_task(self, task: 'ParallelTask', test_runner: 'TestRunner'):
        task.status = "NOTRUN"
        sys.stdout.force_write(f"====>Skipping task {task.name}, {task.test_name} is cancelled\n")
        self._accept_last_task()
        self.complete_task(task, test_runner)

    def __form_task_dependencies(self, task: 'ParallelTask'):
        res = []
        for dep in task.depends:
            if type(dep) is tuple:
                res.append(dep)
            else:
                res.append((dep, dep))
        return res

    def __complete_of_failed_dependency(self, task: 'ParallelTask', test_runner: 'TestRunner', dependency,
                                        dependencies: dict) -> bool:
        for other_task in self.completed_tasks:
            if dependency[0] == other_task.name:
                if other_task.status in ["ERROR", "NOTRUN", "READY"] and task.fail(dependency[0]):
                    task.status = "NOTRUN"
                    sys.stdout.force_write(f"====>Dependency failed {dependency[0]}\n")

                    self._accept_last_task()
                    self.complete_task(task, test_runner)
                    self.dependency_failed = True
                else:
                    dependencies[dependency[1]] = other_task.result

                return True

        return False

    def __process_task_dependencies(self, task: 'ParallelTask', test_runner: 'TestRunner', dependencies: dict
                                    ) -> Tuple[bool, 'ParallelTask', dict]:
        # sys.stdout.force_write(f"===>Checking dependencies for test {task.name}\n")
        depends = self.__form_task_dependencies(task)

        for dependency in depends:
            self.dependency_failed = False
            completed = self.__complete_of_failed_dependency(task, test_runner, dependency, dependencies)

            if not completed:
                # sys.stdout.force_write(f"====>Dependency not completed yet {dependency}\n")
                break
            if self.dependency_failed:
                break
        else:
            self._accept_last_task()

            return False, task, dependencies

        return True, task, dependencies

    def pop_task(self, runner: 'TestRunner'):
        with self.lock:
            counter = 0

            while True:
                counter += 1
                self.__secure_counts(counter)

                task = self.__get_next_in_queue()
                if task is None:
                    self.__put_dep_unsuitable_tasks(runner)
                    return None
                if task.test_name in self.cancelled_tests:
                    self.__skip_cancelled_task(task, runner)
                    break

                dependencies = {}
                if len(task.depends):
                    broken_cycle, task, dependencies = self.__process_task_dependencies(task, runner, dependencies)
                    if not broken_cycle:
                        return task, dependencies
                else:
                    # sys.stdout.force_write(f"No dependencies for test {task.name}\n")
                    self._accept_last_task()
                    return task, dependencies


class TestRunner:
    def __init__(
        self, test_queue: TestQueue, thread_id: int, progress_report_callback, webdriver_manager: WebdriverManager
    ):
        self.test_queue = test_queue
        self.thread = None
        self.thread_id = thread_id
        self.progress_report_callback = progress_report_callback
        self.webdriver_manager = webdriver_manager
        self.current_test = None

    def force_interrupt(self) -> None:
        exception = Exception("Framework thread interrupted, test cancelled")
        found = False
        target_tid = 0
        for tid, tobj in threading._active.items():
            if tobj is self.thread:
                found = True
                target_tid = tid
                break

        if not found:
            raise ValueError("Invalid thread object")

        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), ctypes.py_object(exception))
        if ret == 0:
            raise ValueError("Invalid thread ID")
        elif ret > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")
        print(f"Interrupted {self.thread.name}")

    def launch(self) -> None:
        self.thread = threading.Thread(target=_threaded_method, args=(self,))
        self.thread.start()


class ParallelTask:
    def __init__(
            self,
            func: Callable,
            name: str,
            on_dependency_fail=None,
            depends: Optional[List[Union[Tuple[str, str], str]]] = None,
            webdriver_restart_required=True,
            test_name=None,
    ):
        self.depends = [] if depends is None else depends
        self.status = "READY"
        self.func = func
        self.name = name
        self.test_name = test_name
        self.result = None
        self.on_dependency_fail = on_dependency_fail
        self.webdriver_restart_required = webdriver_restart_required

    def run(self, webdriver_instance: webdriver.Firefox, dependencies):
        self.status = "RUNNING"
        result = self.func(webdriver_instance, dependencies)
        self.status = result[0]
        self.result = result[1]
        return self.result

    def __le__(self, other):
        return self.name.__le__(other.name)

    def __lt__(self, other):
        return self.name.__lt__(other.name)

    def fail(self, dependency) -> bool:
        if self.on_dependency_fail is not None:
            result = self.on_dependency_fail(dependency)
            if result is not None:
                return result
        return True


def _monitor_cancelled_tests(test_runner: TestRunner, monitor_condition=True):
    processed_cancelled_tests = list()

    while monitor_condition:
        for cancelled_test in test_runner.test_queue.cancelled_tests:
            if cancelled_test not in processed_cancelled_tests:
                if test_runner.current_test == cancelled_test:
                    _cancelling_task_progress(
                        test_runner.progress_report_callback, test_runner.current_test, test_runner.thread_id
                    )
                    test_runner.force_interrupt()

                processed_cancelled_tests.append(cancelled_test)
        time.sleep(2)


def _current_test_run_task(test_runner: TestRunner, driver: webdriver.Firefox, task: ParallelTask, dependencies):
    test_runner.status = f"RUNNING {task.name}"
    _running_progress(test_runner.progress_report_callback, test_runner.thread_id, task)
    test_runner.current_test = task.test_name
    logger.info(f"==>Thread {test_runner.thread_id} running {task.name}\n")

    dependencies["progress_report_callback"] = test_runner.progress_report_callback
    dependencies["thread_id"] = test_runner.thread_id

    task.run(driver, dependencies)
    logger.info(
        f"==>Thread {test_runner.thread_id} completed {task.name}:{task.status}\n{sys.stdout.get_log(threading.current_thread())}"
    )
    sys.stdout.reset_log(threading.current_thread())


def _handle_queued_task(test_runner: TestRunner, driver: webdriver.Firefox, idle=False):
    try:
        task_info = test_runner.test_queue.pop_task(test_runner)
    except NoTasksLeftException:
        return 1

    if task_info is None:
        if not idle:
            logger.info(f"==>Thread {test_runner.thread_id} idling")

        time.sleep(3)
        return

    task, dependencies = task_info

    try:
        _current_test_run_task(test_runner, driver, *task_info)
    except Exception as e:
        task.status = "ERROR"
        logger.error(
            f"==>Thread {test_runner.thread_id} encountered an ERROR while running {task.name}:{e}"
            f"\n{traceback.format_exc()}\nLOGS:"
            f"\n{sys.stdout.get_log(threading.current_thread())}"
        )

    test_runner.current_test = None
    _cancelled_progress(test_runner.progress_report_callback, test_runner.thread_id)

    test_runner.test_queue.complete_task(task, test_runner)


def _threaded_method(test_runner: TestRunner) -> None:
    should_monitor_cancelled_tests = True
    test_cancellation_thread = threading.Thread(
        target=_monitor_cancelled_tests,
        args=(test_runner, should_monitor_cancelled_tests),
        name="Test Cancellation Thread",
    )
    test_cancellation_thread.start()

    _start_webdriver_progress(test_runner.progress_report_callback, test_runner.thread_id)
    webdriver_instance = test_runner.webdriver_manager.request()

    while True:
        _ = _handle_queued_task(test_runner, webdriver_instance)
        if _ != 1:
            continue
        break

    test_runner.webdriver_manager.release(webdriver_instance)

    logger.info(f"==>Shutting down cancelled test monitor for {test_runner.thread_id}\n")
    logger.info(f"==>Thread {test_runner.thread_id} terminated\n")


class StdoutManager:
    def __init__(self, original_stdout, debug: bool = False):
        self.original_stdout = original_stdout
        self.lock = threading.Lock()
        self.per_thread_log = dict()
        self.debug = debug

    def write(self, data) -> None:
        if self.debug or threading.current_thread() == threading.main_thread():
            with self.lock:
                self.original_stdout.write(data)
        else:
            with self.lock:
                if threading.current_thread() not in self.per_thread_log:
                    self.per_thread_log[threading.current_thread()] = list()
                self.per_thread_log[threading.current_thread()].append(data)

    def reset_log(self, thread) -> None:
        with self.lock:
            if thread in self.per_thread_log:
                self.per_thread_log[thread].clear()

    def get_log(self, thread) -> str:
        with self.lock:
            if thread in self.per_thread_log:
                log = "".join(self.per_thread_log[thread])
            else:
                log = ""
        return log

    def force_write(self, data) -> None:
        with self.lock:
            print(data, file=self.original_stdout)

    def flush(self) -> None:
        self.original_stdout.flush()


class ScreenshotController:
    def __init__(self):
        self.counter = 1
        self.screenshotted_elements = {}
        self.lock = threading.RLock()

    def __increment(self) -> int:
        with self.lock:
            count = self.counter
            self.counter += 1
        return count

    def __write_screenshots(self, elements, shots: List[Optional[Image]]) -> None:
        for element_number, (element, image) in enumerate(zip(elements, shots)):
            screenshot_id = self.__increment()
            print(f"Saving screenshot {screenshot_id}")

            self.__screenshot_saving_progress(self.progress_report_callback, element_number, len(shots))

            screenshot_filename = f"screenshots/img{screenshot_id}.jpg"
            self.__save_screenshot(screenshot_filename, image, element)

    def __save_screenshot(self, filename: str, image: Optional[Image], problematic_element) -> None:
        if image is not None:
            problematic_element["screenshot"] = filename
            width, height = image.size
            problematic_element["screenshot_height"] = height
            problematic_element["screenshot_width"] = width

            self.screenshotted_elements[problematic_element["element"]] = {
                "screenshot": filename,
                "screenshot_width": width,
                "screenshot_height": height,
            }

            image.convert("RGB").save(filename)

    def __get_screenshot_images(
            self,
            driver: webdriver.Firefox,
            activity: Activity,
            elements_to_screenshot: Union[List[Element], Element]
    ) -> List[Optional[Image]]:
        return Screenshot(driver, elements_to_screenshot, activity, self.__screenshot_taking_progress).get_images()

    @staticmethod
    def __test_demands_no_screenshots(test, test_filter):
        return (
            len(test.problematic_elements) == 0
            or test_filter != "aXe"
            and test.name != test_filter
            or test_filter == "aXe"
            and test.name.startswith("test_")
        )

    def __get_activity_elements_to_screenshot(self, activity: Activity, tests, test_filter):
        elements_to_screenshot = []

        for test in tests[activity.name]:
            if self.__test_demands_no_screenshots(test, test_filter):
                continue

            print("Taking screenshots for " + test.name)
            elements_to_screenshot.extend(self.__get_test_elements_to_screenshot(test.problematic_elements))

        return elements_to_screenshot

    def __get_test_elements_to_screenshot(self, problematic_elements):
        screenshot_candidates = []

        for element_number, element in enumerate(problematic_elements):
            self.__screenshot_existence_progress(
                self.progress_report_callback, element_number, len(problematic_elements)
            )

            if "screenshot" in element:
                self.__update_width_height(element)
            elif "element" in element:
                if element["important_example"]:
                    screenshot_candidates.append(element)

        return screenshot_candidates

    def get_screenshots_creator(self, tests: dict, activities: List[Activity], test_filter: str):
        def _do_screenshots(webdriver_instance: webdriver.Firefox, dependencies, tests=tests, activities=activities):
            with self.lock:
                self.progress_report_callback = dependencies["progress_report_callback"]
                self.thread_id = dependencies["thread_id"]

                for activity in activities:
                    self.__screenshot_loading_progress(self.progress_report_callback)
                    if not test_filter.startswith("test_") and activity.name + "_" + "aXe" in dependencies and dependencies[activity.name + "_aXe"][0] not in tests[activity.name]:
                        tests[activity.name].extend(dependencies[activity.name + "_" + "aXe"])

                    elements_to_screenshot = self.__get_activity_elements_to_screenshot(
                        activity, tests, test_filter
                    )

                    if not elements_to_screenshot:
                        continue

                    print(f"Opening {activity.url}")
                    activity.get(webdriver_instance)
                    # * TOOK here too

                    webdriver_instance.fullscreen_window()
                    if activity.page_resolution:
                        webdriver_instance.set_window_size(*activity.page_resolution)

                    screenshots = self.__get_screenshot_images(
                        webdriver_instance, activity, elements_to_screenshot
                    )

                    assert len(elements_to_screenshot) == len(screenshots), \
                        "Lost screenshots in _get_screenshot_images"

                    self.__write_screenshots(elements_to_screenshot, screenshots)

                return "PASS", None

        return _do_screenshots

    @staticmethod
    def __update_width_height(element):
        img = cv.imread(element["screenshot"])
        element["screenshot_height"] = img.shape[0]
        element["screenshot_width"] = img.shape[1]

    @verify_progress
    def __screenshot_loading_progress(self, progress_report_callback):
        self.progress_report_callback({"additional_info": {self.thread_id: "Loading screenshot data"}})

    @verify_progress
    def __screenshot_existence_progress(self, progress_report_callback, current, total_amount):
        self.progress_report_callback(
            {
                "additional_info": {
                    self.thread_id: f"Checking for existing screenshot of element {current + 1}/{total_amount}",
                }
            }
        )

    def __screenshot_taking_progress(self, current: int, total_amount: int) -> None:
        if self.progress_report_callback is not None:
            self.progress_report_callback(
                {
                    "additional_info": {
                        self.thread_id: f"Taking screenshot {current}/{total_amount}",
                    }
                }
            )

    @verify_progress
    def __screenshot_saving_progress(self, progress_report_callback, current: int, total_amount: int):
        self.progress_report_callback(
            {
                "additional_info": {
                    self.thread_id: f"Saving screenshot {current + 1}/{total_amount}",
                }
            }
        )


class FormTestQueueCapsule:
    def __init__(self, tests: dict, activities: List[Activity], required_elements: set,
                 run_axe_tests: Optional[list] = None):
        self.tests = tests
        self.activities = activities
        self.required_elements = required_elements
        self.all_tests: List[str] = []
        self.tasks: List[Tuple[int, ParallelTask]] = []
        self.axe_tasks: List[ParallelTask] = []
        self.run_axe_tests = run_axe_tests
        self.new_locator_task_name = ""
        self.screenshot_controller = ScreenshotController()

    def form_test_queue(self, testing: bool = False):
        logger.info("=>Forming the task queue")

        if self.run_axe_tests is None or len(self.run_axe_tests) > 0:
            self.__build_queue_of_activities_tasks(testing)

        self.__build_tasks_queue_with_priorities(testing)

        for task in self.tasks:
            print(f"{task[0]} - {task[1].name}")

        return self.tasks, self.axe_tasks

    def __build_queue_of_activities_tasks(self, testing: bool) -> None:
        page_activities = list()
        known_urls = set()

        for activity in self.activities:
            if activity.url not in known_urls:
                known_urls.add(activity.url)
                page_activities.append(activity)

        for activity in page_activities:

            def _run_axe(webdriver_instance, dependencies, activity=activity) -> Tuple[str, List[ImportedTest]]:
                # authorization with axe causes really nasty connection error
                # cant' perform activity.get(webdriver_instance), so authenticate
                webdriver_instance.maximize_window()

                if activity.page_resolution:
                    webdriver_instance.set_window_size(*activity.page_resolution)
                pseudo_tests = axe_integration.run_tests(webdriver_instance, activity, self.run_axe_tests)

                return "PASS", pseudo_tests

            axe_task = ParallelTask(
                _run_axe, activity.name + "_" + "aXe", None, [], webdriver_restart_required=False, test_name="aXe"
            )
            self.axe_tasks.append(axe_task)
            # Axe tasks are prioritized - they are very fast
            self.tasks.append((-10, axe_task))
            self.all_tests.append(activity.name + "_" + "aXe")

        if not testing:
            for axe_test in self.run_axe_tests:
                self.tasks.append(
                    (
                        100000,
                        ParallelTask(
                            self.screenshot_controller.get_screenshots_creator(self.tests, self.activities, axe_test),
                            "screenshots_aXe_"+axe_test,
                            lambda dependency: False,
                            [axe_task.name for axe_task in self.axe_tasks],
                            test_name=axe_test,
                        ),
                    )
                )

    def __append_locator_task(self, activity):
        def _run_locator(webdriver_instance, dependencies, activity=activity) -> Tuple[str, ElementLocator]:
            # * authorize by get -> open -> auth_by_options
            activity.get(webdriver_instance)

            webdriver_instance.maximize_window()
            element_locator = ElementLocator(webdriver_instance, activity, self.required_elements)
            element_locator.analyze()

            return "PASS", element_locator

        self.new_locator_task_name = "locator_" + activity.name
        # ? -5 is for sort only
        self.tasks.append((-5, ParallelTask(_run_locator, self.new_locator_task_name)))

    def __build_tasks_queue_with_priorities(self, testing: bool) -> None:
        for activity in self.activities:
            self.__append_locator_task(activity)
            testing_tasks = self.__build_parallel_testing_tasks(activity)

            for priority, task in enumerate(testing_tasks):
                self.tasks.append((priority, task[1]))
                if not testing:
                    self.__append_screenshot_parallel_for_task(task)

    def __build_parallel_testing_tasks(self, activity: Activity):
        testing_tasks = []

        for test in self.tests[activity.name]:  # * Main Page_Main Activity,

            run_test_inst = RunTestShell(test, activity, self.new_locator_task_name)

            deps = [(activity.name + "_" + dep, dep) for dep in test.depends if dep.startswith("test_")]
            deps.extend([dep for dep in test.depends if not dep.startswith("test_")])

            parallel_task = ParallelTask(
                run_test_inst.run_test,
                activity.name + "_" + test.name,
                on_dependency_fail=run_test_inst.fail_test,
                depends=[self.new_locator_task_name] + deps,
                webdriver_restart_required=test.webdriver_restart_required,
                test_name=test.name,
            )

            testing_tasks.append((test.name, parallel_task))
            self.all_tests.extend([activity.name + "_" + test.name for test in self.tests[activity.name]])

        # Prioritize tasks without dependencies, then sort ignoring activity name,
        # so that all activities for 1 test are done first
        testing_tasks.sort(
            key=lambda task: (len(task[1].depends), 1 if task[1].webdriver_restart_required else 0, task[0])
        )

        return testing_tasks

    def __append_screenshot_parallel_for_task(self, task):
        self.tasks.append(
            (
                100000,
                ParallelTask(
                    self.screenshot_controller.get_screenshots_creator(
                        self.tests, self.activities, task[1].test_name
                    ),
                    "screenshots_" + task[1].test_name,
                    depends=[task[1].name],
                    test_name=task[1].test_name,
                ),
            )
        )


class RunTestShell:
    """Saves environment for test run"""

    def __init__(self, test, activity, new_locator_task_name: str) -> None:
        self.test = test
        self.activity = activity
        self.locator_task_name = new_locator_task_name

    def fail_test(self, dependency) -> None:
        self.test.status = "NOTRUN"
        self.test.message = "Dependency failed: " + dependency

    def run_test(self, webdriver_instance, dependencies):
        webdriver_instance.maximize_window()

        if len(dependencies) > 3:
            self.test.run(webdriver_instance, self.activity, dependencies[self.locator_task_name], dependencies)
        else:
            self.test.run(webdriver_instance, self.activity, dependencies[self.locator_task_name])

        for problematic_element in self.test.problematic_elements:
            problematic_element["page_url"] = self.activity.url
            problematic_element["page_resolution"] = self.activity.page_resolution

        return self.test.status, self.test.result


def _build_nontest_deps(tests):
    nontest_deps = set()

    for testlist in tests.values():
        for test in testlist:
            nontest_deps.update(test.depends)

    return set(filter(lambda i: not i.startswith("test_"), nontest_deps))


def _form_tasks_with_models(tasks: List[Tuple[int, ParallelTask]], nontest_dependencies):
    prev_model_unload = []

    for model_name in nontest_dependencies:

        def load_model(webdriver_instance, dependencies, model_name=model_name):
            return "PASS", model_wrapper.load(model_name=model_name)

        def unload_model(webdriver_instance, dependencies, model_name=model_name):
            return "PASS", dependencies[model_name].unload()

        tasks_needing_model = list()
        for task in tasks:
            if model_name in task[1].depends:
                tasks_needing_model.append(task)

        if prev_model_unload:
            tasks.append(
                (
                    0,
                    ParallelTask(
                        load_model, model_name, None, list(prev_model_unload), webdriver_restart_required=False
                    ),
                )
            )
        else:
            tasks.append((0, ParallelTask(load_model, model_name, webdriver_restart_required=False)))

        tasks.append(
            (
                0,
                ParallelTask(
                    unload_model,
                    "unload_" + model_name,
                    lambda dependency: False,
                    [task[1].name for task in tasks_needing_model] + [model_name],
                    webdriver_restart_required=False,
                ),
            )
        )
        prev_model_unload.append("unload_" + model_name)


def _launch_threads_test_runners(test_queue: TestQueue, webdriver_manager: WebdriverManager, threads: List[TestRunner],
                                 thread_count: int,
                                 progress):
    for thread_id in range(thread_count):
        logger.info(f"==>Launching thread {thread_id}")
        test_runner = TestRunner(test_queue, thread_id, progress, webdriver_manager)
        threads.append(test_runner)
        test_runner.launch()


def _run_tests_from_queue(
        tests,
        tasks: List[Tuple[int, ParallelTask]],
        thread_count: int,
        axe_tasks: List[ParallelTask],
        webdriver_manager: WebdriverManager,
        activities: List[Activity],
        report_progress_callback=None,
        do_test_merge=True,
        cancelled_tests=None,
) -> None:
    threads: List[TestRunner] = list()
    if cancelled_tests is None:
        cancelled_tests = []

    nontest_deps = _build_nontest_deps(tests)
    _form_tasks_with_models(tasks, nontest_deps)
    _running_tasks_progress(report_progress_callback, len(tasks))

    test_queue = TestQueue(
        tasks, tests, axe_tasks, activities, cancelled_tests=cancelled_tests, do_interim_results=do_test_merge
    )

    logger.info("=>Setting up the stdout manager")
    sys.stdout = StdoutManager(sys.stdout, debug=thread_count == 1)
    logger.info(f"=>Launching the {thread_count} threads")

    _launch_threads_test_runners(test_queue, webdriver_manager, threads, thread_count, report_progress_callback)

    for thread in threads:
        thread.thread.join()
    logger.info("=>Restoring stdout")
    sys.stdout = sys.stdout.original_stdout

    _unload_models_progress(report_progress_callback)
    model_wrapper.unload_all()


def run_tests_in_parallel(
        tests: dict,
        activities: List[Activity],
        thread_count: int,
        required_elements,
        webdriver_manager: WebdriverManager,
        report_progress_callback=None,
        run_axe_tests=None,
        testing: bool = False,
        do_test_merge=True,
        cancelled_tests=None,
) -> None:
    tasks, axe_tasks = FormTestQueueCapsule(
        tests, activities, required_elements, run_axe_tests=run_axe_tests
    ).form_test_queue(testing)

    _run_tests_from_queue(
        tests,
        tasks,
        thread_count,
        axe_tasks,
        webdriver_manager,
        activities,
        report_progress_callback,
        do_test_merge=do_test_merge,
        cancelled_tests=cancelled_tests,
    )
