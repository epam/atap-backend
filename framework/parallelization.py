import ctypes
import logging
import sys
import threading
import time
import traceback
from queue import PriorityQueue
from typing import List

import cv2 as cv

# from copy import deepcopy

from framework import model_wrapper, axe_integration
from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.screenshot.screenshot import Screenshot
from framework.webdriver_manager import WebdriverManager


logger = logging.getLogger("framework.parallelization")


class NoTasksLeftException(Exception):
    pass


class TestQueue:
    def __init__(self, tasks, tests, axe_tasks, activities: List[Activity], cancelled_tests, do_interim_results=False):
        self.task_queue = PriorityQueue()
        self._verify_dependencies(tasks)
        for task in tasks:
            self.task_queue.put(task)
        self.tests = tests
        self.axe_tasks = axe_tasks
        self.do_interim_results = do_interim_results
        self.activities = activities
        self.completed_tasks = []
        self.running_tasks = []
        self.lock = threading.RLock()
        self.unsuitable_tasks = []
        self.cancelled_tests = cancelled_tests
        self.finished_tests = {}
        self.screenshotted_tests = []

    def complete_task(self, task, runner):
        with self.lock:
            self.running_tasks.remove(task)
            # if task.name.startswith("screenshots_"):
            #     if runner.progress_report_callback is not None:
            #         runner.progress_report_callback({
            #             "interim_test_result": finished_test
            #         })
            if task.name.startswith("screenshot"):
                if task.test_name == "aXe":
                    if runner.progress_report_callback is not None:
                        # for axe_task in self.axe_tasks:
                        #     for axe_test in axe_task.result:
                        #         runner.progress_report_callback({
                        #             "screenshots_for_test": axe_test
                        #         })
                        for axe_test in self.finished_tests["aXe"]:
                            runner.progress_report_callback({"screenshots_for_test": axe_test})
                elif (
                    runner.progress_report_callback is not None
                    and self.finished_tests[task.test_name] not in self.screenshotted_tests
                ):
                    runner.progress_report_callback({"screenshots_for_test": self.finished_tests[task.test_name]})
                    self.screenshotted_tests.append(self.finished_tests[task.test_name])
            elif task.test_name is not None and not task.name.startswith("screenshot") and self.do_interim_results:
                tasks_in_queue = list(map(lambda x: x[1], self.task_queue.queue))
                unfinished_tasks_of_type = [
                    t
                    for t in tasks_in_queue + self.running_tasks
                    if t.test_name == task.test_name and not t.name.startswith("screenshot")
                ]
                if unfinished_tasks_of_type:
                    print(f"Task {task.name} finished, but {len(unfinished_tasks_of_type)} tasks of type remain")
                elif task.test_name == "aXe":
                    print("Submitting axe interim results")
                    pseudo_tests = []
                    for axe_task in self.axe_tasks:
                        logger.info("AXE TASK " + axe_task.name)
                        if axe_task.result is not None:
                            for axe_test in axe_task.result:
                                for pseudo_test in pseudo_tests:
                                    if pseudo_test.name == axe_test.name:
                                        pseudo_test.merge_other_test(axe_test)
                                        break
                                else:
                                    # pseudo_tests.append(deepcopy(axe_test))
                                    pseudo_tests.append(axe_test)

                    for pseudo_test in pseudo_tests:
                        if runner.progress_report_callback is not None:
                            runner.progress_report_callback({"interim_test_result": pseudo_test})
                    self.finished_tests["aXe"] = pseudo_tests

                else:
                    print(f"Submitting interim results for {task.test_name}")
                    # tests_values_fixed_order = [deepcopy(test) for test in self.tests.values()]
                    tests_values_fixed_order = [test for test in self.tests.values()]

                    for test in tests_values_fixed_order[0]:
                        if test.name == task.test_name:
                            finished_test = test
                            for activity_tests in tests_values_fixed_order[1:]:
                                for secondary_test in activity_tests:
                                    if finished_test.name == secondary_test.name:
                                        finished_test.merge_other_test(secondary_test)
                            break
                    else:
                        raise ValueError(f"Could not find {task.test_name} in test list")

                    self.finished_tests[finished_test.name] = finished_test

                    if runner.progress_report_callback is not None:
                        runner.progress_report_callback({"interim_test_result": finished_test})

            self.completed_tasks.append(task)
            if runner.progress_report_callback is not None:
                runner.progress_report_callback({"tasks_complete": len(self.completed_tasks)})

    def _get_next_in_queue(self):
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
    def _verify_dependencies(task_list):
        task_names = [other_task[1].name for other_task in task_list]
        for task in task_list:
            deps = task[1].depends
            for dep in deps:
                if type(dep) is tuple:
                    dep = dep[0]
                if dep not in task_names:
                    raise ValueError(f"DEPENDENCY ERROR: Task {task[1].name} has an unmet dependency {dep}")

    def pop_task(self, runner):
        with self.lock:
            counter = 0
            MAX_TRIES = 10000
            while True:
                counter += 1
                if counter > MAX_TRIES:
                    logger.fatal("pop_task is in an endless loop!")
                    while not self.task_queue.empty():
                        task = self.task_queue.get()[1]
                        logger.fatal(f"{task.name} - {task.depends} ")
                    raise ValueError("pop_task is in an endless loop!")
                task = self._get_next_in_queue()
                if task is None:
                    if len(self.unsuitable_tasks) == 0:
                        if runner.progress_report_callback is not None:
                            runner.progress_report_callback(
                                {"thread_status": {runner.thread_id: "IDLE: No more work"}}
                            )

                        raise NoTasksLeftException
                    else:
                        if runner.progress_report_callback is not None:
                            runner.progress_report_callback(
                                {"thread_status": {runner.thread_id: "IDLE: Waiting for dependencies to resolve"}}
                            )

                        self._restore_unsuitable_tasks()
                        return None

                if task.test_name in self.cancelled_tests:
                    task.status = "NOTRUN"
                    sys.stdout.force_write(f"====>Skipping task {task.name}, {task.test_name} is cancelled\n")
                    self._accept_last_task()
                    self.complete_task(task, runner)
                    break
                dependencies = {}
                if len(task.depends):
                    # sys.stdout.force_write(f"===>Checking dependencies for test {task.name}\n")
                    depends = []
                    for dep in task.depends:
                        if type(dep) is tuple:
                            depends.append(dep)
                        else:
                            depends.append((dep, dep))

                    for dependency in depends:
                        dependency_failed = False
                        for other_task in self.completed_tasks:
                            if dependency[0] == other_task.name:
                                if (
                                    other_task.status
                                    in [
                                        "ERROR",
                                        "NOTRUN",
                                        "READY",
                                    ]
                                    and task.fail(dependency[0])
                                ):
                                    task.status = "NOTRUN"
                                    sys.stdout.force_write(f"====>Dependency failed {dependency[0]}\n")
                                    self._accept_last_task()
                                    self.complete_task(task, runner)
                                    dependency_failed = True
                                else:
                                    dependencies[dependency[1]] = other_task.result
                                break
                        else:
                            # sys.stdout.force_write(f"====>Dependency not completed yet {dependency}\n")
                            break
                        if dependency_failed:
                            break
                    else:
                        self._accept_last_task()
                        return task, dependencies
                else:
                    # sys.stdout.force_write(f"No dependencies for test {task.name}\n")
                    self._accept_last_task()
                    return task, dependencies


class TestRunner:
    def __init__(
            self,
            test_queue: TestQueue,
            thread_id: int,
            progress_report_callback,
            webdriver_manager: WebdriverManager,
    ):
        self.test_queue = test_queue
        self.thread = None
        self.thread_id = thread_id
        self.progress_report_callback = progress_report_callback
        self.webdriver_manager = webdriver_manager
        self.current_test = None

    def force_interrupt(self):
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
        self.thread = threading.Thread(target=threaded_method, args=(self,))
        self.thread.start()


class ParallelTask:
    def __init__(
            self,
            func,
            name: str,
            on_dependency_fail=None,
            depends=None,
            webdriver_restart_required=True,
            test_name=None
    ):
        self.depends = [] if depends is None else depends
        self.status = "READY"
        self.func = func
        self.name = name
        self.test_name = test_name
        self.result = None
        self.on_dependency_fail = on_dependency_fail
        self.webdriver_restart_required = webdriver_restart_required

    def run(self, webdriver_instance, dependencies):
        self.status = "RUNNING"
        result = self.func(webdriver_instance, dependencies)
        self.status = result[0]
        self.result = result[1]
        return result[1]

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


def threaded_method(test_runner: TestRunner):
    should_monitor_cancelled_tests = True

    def monitor_cancelled_tests():
        processed_cancelled_tests = list()
        while should_monitor_cancelled_tests:
            for cancelled_test in test_runner.test_queue.cancelled_tests:
                if cancelled_test not in processed_cancelled_tests:
                    if (
                        test_runner.current_test == cancelled_test
                        and test_runner.progress_report_callback is not None
                    ):
                        test_runner.progress_report_callback(
                            {
                                "thread_status": {
                                    test_runner.thread_id: f"Cancelling {test_runner.current_test}",
                                },
                                "thread_task_cancellable": {
                                    test_runner.thread_id: False,
                                },
                            }
                        )
                        test_runner.force_interrupt()
                    processed_cancelled_tests.append(cancelled_test)

            time.sleep(2)

    test_cancellation_thread = threading.Thread(target=monitor_cancelled_tests, name="Test Cancellation Thread")
    test_cancellation_thread.start()

    idle = False
    if test_runner.progress_report_callback is not None:
        test_runner.progress_report_callback(
            {
                "thread_status": {
                    test_runner.thread_id: f"Starting webdriver...",
                }
            }
        )
    webdriver_instance = test_runner.webdriver_manager.request()
    while True:
        try:
            task_info = test_runner.test_queue.pop_task(test_runner)
        except NoTasksLeftException:
            break
        if task_info is None:
            if not idle:
                logger.info(f"==>Thread {test_runner.thread_id} idling")
                idle = True
            time.sleep(3)
            continue
        idle = False
        (task, dependencies) = task_info
        try:
            test_runner.status = f"RUNNING {task.name}"
            if test_runner.progress_report_callback is not None:
                test_runner.progress_report_callback(
                    {
                        "thread_status": {
                            test_runner.thread_id: f"Running {task.name}",
                        },
                        "thread_task_cancellable": {
                            test_runner.thread_id: task.test_name is not None and task.test_name != "aXe",
                        },
                        "thread_test_name": {
                            test_runner.thread_id: task.test_name,
                        },
                    }
                )
            test_runner.current_test = task.test_name
            logger.info(f"==>Thread {test_runner.thread_id} running {task.name}\n")
            dependencies["progress_report_callback"] = test_runner.progress_report_callback
            dependencies["thread_id"] = test_runner.thread_id

            task.run(webdriver_instance, dependencies)
            logger.info(
                f"==>Thread {test_runner.thread_id} completed {task.name}:{task.status}\n{sys.stdout.get_log(threading.current_thread())}"
            )
            sys.stdout.reset_log(threading.current_thread())
        except Exception as e:
            task.status = "ERROR"
            logger.error(
                f"==>Thread {test_runner.thread_id} encountered an ERROR while running {task.name}:{e}"
                f"\n{traceback.format_exc()}\nLOGS:"
                f"\n{sys.stdout.get_log(threading.current_thread())}"
            )
        test_runner.current_test = None
        if test_runner.progress_report_callback is not None:
            test_runner.progress_report_callback(
                {
                    "thread_task_cancellable": {
                        test_runner.thread_id: False,
                    },
                    "thread_test_name": {
                        test_runner.thread_id: None,
                    },
                }
            )

        test_runner.test_queue.complete_task(task, test_runner)
    test_runner.webdriver_manager.release(webdriver_instance)
    should_monitor_cancelled_tests = False
    logger.info(f"==>Shutting down cancelled test monitor for {test_runner.thread_id}\n")
    test_cancellation_thread.join()
    logger.info(f"==>Thread {test_runner.thread_id} terminated\n")


class StdoutManager:
    def __init__(self, original_stdout, debug=False):
        self.original_stdout = original_stdout
        self.lock = threading.Lock()
        self.per_thread_log = dict()
        self.debug = debug

    def write(self, data) -> None:
        if self.debug or threading.current_thread() == threading.main_thread():
            with self.lock:
                self.original_stdout.write(f"[{threading.current_thread()}] {data}")
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

    def _increment(self) -> int:
        with self.lock:
            count = self.counter
            self.counter += 1
        return count

    def _write_screenshots(self, elements, shots) -> None:
        for element_number, (element, image) in enumerate(zip(elements, shots)):
            screenshot_id = self._increment()
            print(f"Saving screenshot {screenshot_id}")
            self._screenshot_saving_progress(element_number, len(shots))

            screenshot_filename = f"screenshots/img{screenshot_id}.jpg"
            self._save_screenshot(screenshot_filename, image, element)

    def _save_screenshot(self, filename, image, problematic_element) -> None:
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

    def _get_screenshot_images(self, driver, activity: Activity, elements_to_screenshot):
        return Screenshot(driver, elements_to_screenshot).get_images(
            self.screenshot_taking_progress, activity=activity
        )

    @staticmethod
    def _test_demands_no_screenshots(test, test_filter) -> bool:
        return (
            len(test.problematic_elements) == 0
            or test_filter != "aXe"
            and test.name != test_filter
            or test_filter == "aXe"
            and test.name.startswith("test_")
        )

    def _get_activity_elements_to_screenshot(self, activity: Activity, tests, test_filter):
        elements_to_screenshot = []

        for test in tests[activity.name]:
            if self._test_demands_no_screenshots(test, test_filter):
                continue

            print("Taking screenshots for " + test.name)
            elements_to_screenshot.extend(self._get_test_elements_to_screenshot(test.problematic_elements))

        return elements_to_screenshot

    def _get_test_elements_to_screenshot(self, problematic_elements):
        screenshot_candidates = []

        for element_number, element in enumerate(problematic_elements):
            self._screenshot_existence_progress(element_number, len(problematic_elements))

            if "screenshot" in element:
                self._update_width_height(element)
            elif "element" in element:
                screenshot_candidates.append(element)

        return screenshot_candidates

    def get_screenshots_creator(self, tests, activities: List[Activity], test_filter):
        def do_screenshots(webdriver_instance, dependencies, tests=tests, activities: List[Activity] = activities):
            with self.lock:
                self.progress_report_callback = dependencies["progress_report_callback"]
                self.thread_id = dependencies["thread_id"]

                for activity in activities:
                    print(f"Opening {activity.url}")

                    activity.get(webdriver_instance)
                    webdriver_instance.fullscreen_window()

                    if test_filter == "aXe" and activity.name + "_" + "aXe" in dependencies:
                        tests[activity.name].extend(dependencies[activity.name + "_" + "aXe"])

                    self._screenshot_loading_progress()
                    elements_to_screenshot = self._get_activity_elements_to_screenshot(activity, tests, test_filter)

                    if not elements_to_screenshot:
                        continue
                    screenshots = self._get_screenshot_images(webdriver_instance, activity, elements_to_screenshot)

                    assert len(screenshots) == len(elements_to_screenshot), "Lost screenshots in _get_screenshot_images"

                    self._write_screenshots(elements_to_screenshot, screenshots)

                return "PASS", None

        return do_screenshots

    @staticmethod
    def _update_width_height(element):
        img = cv.imread(element["screenshot"])
        element["screenshot_height"] = img.shape[0]
        element["screenshot_width"] = img.shape[1]

    def _screenshot_loading_progress(self):
        if self.progress_report_callback is not None:
            self.progress_report_callback({"additional_info": {self.thread_id: "Loading screenshot data"}})

    def _screenshot_existence_progress(self, current, total_amount):
        if self.progress_report_callback is not None:
            self.progress_report_callback(
                {
                    "additional_info": {
                        self.thread_id: f"Checking for existing screenshot of element {current + 1}/{total_amount}",
                    }
                }
            )

    def screenshot_taking_progress(self, current, total_amount):
        if self.progress_report_callback is not None:
            self.progress_report_callback(
                {
                    "additional_info": {
                        self.thread_id: f"Taking screenshot {current}/{total_amount}",
                    }
                }
            )

    def _screenshot_saving_progress(self, current, total_amount):
        if self.progress_report_callback is not None:
            self.progress_report_callback(
                {
                    "additional_info": {
                        self.thread_id: f"Saving screenshot {current + 1}/{total_amount}",
                    }
                }
            )


def form_test_queue(
        tests,
        activities: List[Activity],
        required_elements,
        chromespawn,
        run_axe_tests=None,
        testing=False,
):
    logger.info("=>Forming the task queue")
    tasks = list()

    axe_tasks = list()

    all_tests = list()

    screenshot_controller = ScreenshotController()

    if run_axe_tests is None or len(run_axe_tests) > 0:

        page_activities = list()
        known_urls = set()
        for activity in activities:
            if activity.url not in known_urls:
                known_urls.add(activity.url)
                page_activities.append(activity)

        for activity in page_activities:

            def run_axe(webdriver_instance, dependencies, activity=activity):
                # authorization with axe causes really nasty connection error
                # cant' perform activity.get(webdriver_instance), so authenticate

                webdriver_instance.maximize_window()
                pseudo_tests = axe_integration.run_tests(webdriver_instance, activity, run_axe_tests)
                return "PASS", pseudo_tests

            axe_task = ParallelTask(
                run_axe, activity.name + "_" + "aXe", None, [], webdriver_restart_required=False, test_name="aXe"
            )
            axe_tasks.append(axe_task)
            # Axe tasks are prioritized - they are very fast
            tasks.append((-10, axe_task))
            all_tests.append(activity.name + "_" + "aXe")

        if not testing:
            tasks.append(
                (
                    100000,
                    ParallelTask(
                        screenshot_controller.get_screenshots_creator(tests, activities, "aXe"),
                        "screenshots_aXe",
                        lambda dependency: False,
                        [axe_task.name for axe_task in axe_tasks],
                        test_name="aXe",
                    ),
                )
            )

    for activity in activities:

        def run_locator(webdriver_instance, dependencies, activity=activity):
            # * authorize by get -> open -> auth_by_options
            activity.get(webdriver_instance)

            webdriver_instance.maximize_window()
            element_locator = ElementLocator(webdriver_instance, activity, required_elements)
            element_locator.analyze()
            return "PASS", element_locator

        locator_task_name = "locator_" + activity.name
        tasks.append((-5, ParallelTask(run_locator, locator_task_name)))

        testing_tasks = list()
        for test in tests[activity.name]:

            def run_test(
                webdriver_instance, dependencies, test=test, activity=activity, locator_task_name=locator_task_name
            ):
                webdriver_instance.maximize_window()
                start_time = time.time()
                if len(dependencies) > 3:
                    test.run(webdriver_instance, activity, dependencies[locator_task_name], dependencies)
                else:
                    test.run(webdriver_instance, activity, dependencies[locator_task_name])
                test.execution_time = time.time() - start_time
                for problematic_element in test.problematic_elements:
                    problematic_element["page_url"] = activity.url
                return test.status, test.result

            def fail_test(dependency):
                test.status = "NOTRUN"
                test.message = "Dependency failed: " + dependency

            deps = [(activity.name + "_" + dep, dep) for dep in test.depends if dep.startswith("test_")]
            deps += [dep for dep in test.depends if not dep.startswith("test_")]

            parallel_task = ParallelTask(
                run_test,
                activity.name + "_" + test.name,
                fail_test,
                [locator_task_name] + deps,
                webdriver_restart_required=test.webdriver_restart_required,
                test_name=test.name,
            )

            testing_tasks.append((test.name, parallel_task))

            all_tests.extend([activity.name + "_" + test.name for test in tests[activity.name]])

        # Prioritize tasks without dependencies, then sort ignoring activity name,
        # so that all activities for 1 test are done first
        testing_tasks.sort(
            key=lambda task: (len(task[1].depends), 1 if task[1].webdriver_restart_required else 0, task[0])
        )

        priority = 0
        for task in testing_tasks:
            tasks.append((priority, task[1]))
            if not testing:
                tasks.append(
                    (
                        100000,
                        ParallelTask(
                            screenshot_controller.get_screenshots_creator(tests, activities, task[1].test_name),
                            "screenshots_" + task[1].test_name,
                            None,
                            [task[1].name],
                            test_name=task[1].test_name,
                        ),
                    )
                )
            priority += 1

    for task in tasks:
        print(f"{task[0]} - {task[1].name}")
    return tasks, axe_tasks


def run_tests_from_queue(
        tests,
        tasks,
        thread_count: int,
        axe_tasks,
        webdriver_manager: WebdriverManager,
        activities: List[Activity],
        report_progress_callback=None,
        do_test_merge=True,
        cancelled_tests=None,
):
    if cancelled_tests is None:
        cancelled_tests = []
    nontest_deps = set()
    for testlist in tests.values():
        for test in testlist:
            nontest_deps.update(test.depends)

    nontest_deps = set(filter(lambda i: not i.startswith("test_"), nontest_deps))

    prev_model_unload = []

    for dep_id, dep in enumerate(nontest_deps):

        def load_model(webdriver_instance, dependencies, model_name=dep):
            return "PASS", model_wrapper.load(model_name=model_name)

        def unload_model(webdriver_instance, dependencies, model_name=dep):
            return "PASS", dependencies[model_name].unload()

        tasks_needing_model = list()
        for task in tasks:
            if dep in task[1].depends:
                tasks_needing_model.append(task)

        if prev_model_unload:
            tasks.append(
                (0, ParallelTask(load_model, dep, None, list(prev_model_unload), webdriver_restart_required=False))
            )
        else:
            tasks.append((0, ParallelTask(load_model, dep, webdriver_restart_required=False)))
        tasks.append(
            (
                0,
                ParallelTask(
                    unload_model,
                    "unload_" + dep,
                    lambda dependency: False,
                    [task[1].name for task in tasks_needing_model] + [dep],
                    webdriver_restart_required=False,
                ),
            )
        )
        prev_model_unload.append("unload_" + dep)

    if report_progress_callback is not None:
        report_progress_callback({"tasks_count": len(tasks), "overall_progress": f"Running parallel tasks"})

    test_queue = TestQueue(
        tasks, tests, axe_tasks, activities, cancelled_tests=cancelled_tests, do_interim_results=do_test_merge
    )
    logger.info("=>Setting up the stdout manager")
    sys.stdout = StdoutManager(sys.stdout, debug=True)
    logger.info(f"=>Launching the {thread_count} threads")
    threads = list()
    for thread_id in range(thread_count):
        logger.info(f"==>Launching thread {thread_id}")
        test_runner = TestRunner(test_queue, thread_id, report_progress_callback, webdriver_manager)
        threads.append(test_runner)
        test_runner.launch()

    for thread in threads:
        thread.thread.join()

    logger.info("=>Restoring stdout")
    sys.stdout = sys.stdout.original_stdout
    if report_progress_callback is not None:
        report_progress_callback(
            {
                "overall_progress": f"Unloading models",
                "thread_status": {i: "Parallel tasks finished" for i in range(16)},
            }
        )
    model_wrapper.unload_all()
    # pseudo_tests = list()
    # for axe_task in axe_tasks:
    #     logger.info("AXE TASK " + axe_task.name)
    #     if axe_task.result is not None:
    #         for axe_test in axe_task.result:
    #             for pseudo_test in pseudo_tests:
    #                 if pseudo_test.name == axe_test.name:
    #                     pseudo_test.merge_other_test(axe_test)
    #                     break
    #             else:
    #                 pseudo_tests.append(axe_test)
    #
    # return pseudo_tests


def run_tests_in_parallel(
        tests,
        activities: List[Activity],
        thread_count: int,
        required_elements,
        webdriver_manager: WebdriverManager,
        report_progress_callback=None,
        run_axe_tests=None,
        testing=False,
        do_test_merge=True,
        cancelled_tests=None,
):
    if cancelled_tests is None:
        cancelled_tests = []
    tasks, axe_tasks = form_test_queue(
        tests, activities, required_elements, webdriver_manager, run_axe_tests, testing
    )
    return run_tests_from_queue(
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
