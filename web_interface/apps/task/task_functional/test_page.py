import base64
import logging
import threading
from copy import deepcopy
from json import dumps
from re import sub, DOTALL
from socket import timeout
from tempfile import NamedTemporaryFile
from time import time, sleep
from traceback import format_exc
from typing import Tuple, Callable, Optional, List

from django.conf import settings
from kombu import Queue, Connection, Exchange

from framework.main import discover_and_run
from web_interface.apps.task.models import Task
from web_interface.apps.task.task_functional.estimate_time import (
    calculate_job_tests_pages_and_its_timings,
    task_accepting_order_estimated_runtimes,
)


def init_root_logger():
    logger = logging.getLogger("framework")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    console = logging.StreamHandler()
    logger.addHandler(console)

    return logger, console


root_logger, _ = init_root_logger()


class TestPageStatusCapsule:
    def __init__(self, shared_task, project_info, task_id, worker_key):
        self.shared_task = shared_task
        self.project_info = project_info
        self.task_id = task_id
        self.worker_key = worker_key

        self.log_file = None
        self.log_file_handler = None
        self.log = None

        self.receive_worker_messages = True
        self.worker_communicator = None

        self.keepalive = True
        self.keepalive_thread = None
        self.progress = None
        self.lock = threading.RLock()
        self.rabbitmq_outbound_lock = threading.Lock()

        self.time_testing_started = time()
        self.test_timings = None

    def test_page_func(self) -> None:
        self.__toggle_test_page_logging()
        self.__instantiate_worker_communicator()

        self.__build_progress_bar_estimates_queue()

        queue, connection, producer, worker_communication_thread = self.__get_communication_providers(
            self.task_id,
            self.worker_communicator.receive_worker_communication_messages,
            self.receive_worker_messages,
        )
        self.__instantiate_progress(producer, queue)

        try:
            self.__run_tasks(connection)
            self.__finish_job()
        except Exception as exc:
            root_logger.exception(f"Test Page Exception {exc}\n{format_exc()}\n")
            self.__stop_communication(worker_communication_thread)

        self.__close_connection(connection, producer)

    def publish_with_producer(self, type_="default", extended_info: Optional[dict] = None) -> None:
        if extended_info is None:
            extended_info = {}
        producer, queue, task_id, worker_key = [
            getattr(self.progress, key) for key in ("producer", "queue", "task_id", "worker_key")
        ]

        with self.rabbitmq_outbound_lock:
            producer.publish(
                {"worker_key": worker_key, "type": type_, "task_id": task_id, **extended_info},
                retry=True,
                exchange=queue.exchange,
                routing_key=queue.routing_key,
                declare=[queue],
            )

    def get_running_time(self) -> int:
        return int(time() - self.time_testing_started)

    def save_log(self, crash: bool = False) -> None:
        if crash:
            print("Saving crash log...")
        root_logger.removeHandler(self.log_file_handler)
        self.log_file.seek(0)
        self.log = self.log_file.read().decode(encoding="utf-8")
        self.log_file.close()

    def __instantiate_progress(self, producer: Connection.Producer, queue: Queue) -> None:
        self.progress = ProgressStateCapsule(self, producer, queue)

    def __instantiate_worker_communicator(self) -> None:
        self.worker_communicator = WorkerMessagesCapsule(self.task_id)

    def __post_task_running(self, request_id):
        self.publish_with_producer(type_="set_running", extended_info={"celery_task_id": request_id})

    def __finish_testing_and_upload_to_server(self, result) -> None:
        self.publish_with_producer(type_="results", extended_info={"result": result})
        self.publish_with_producer(type_="finish", extended_info={})

    def __build_progress_bar_estimates_queue(self) -> None:
        _, pages, test_names, simulated_test_timings = calculate_job_tests_pages_and_its_timings(
            job=Task.objects.get(id=self.task_id).target_job
        )
        self.test_timings = task_accepting_order_estimated_runtimes(pages, test_names, simulated_test_timings)
        next(self.test_timings)  # * build generator
        self.test_timings.send(None)

    def __run_tasks(self, connection: Connection) -> None:
        self.__post_task_running(self.shared_task.request.id)
        self.__start_testing_keepalive_thread(connection)
        self.project_info["task_id"] = self.shared_task.request.id

        axe_test_list = self.__build_axe_test_list(self.project_info)
        # * framework tests
        discover_and_run(
            project_info=self.project_info,
            filter_test=[test for test in self.project_info["tests"] if test.startswith("test")],
            run_axe_tests=axe_test_list,
            progress_report_callback=self.progress.report_progress,
            cancelled_tests=self.worker_communicator.cancelled_tests,
        )

    def __finish_job(self) -> None:
        result_data = self.progress.progress_uploading_to_server()
        self.__shutdown_keepalive()
        self.__finish_testing_and_upload_to_server(result_data)

    def __post_keepalive(self, connection: Connection) -> None:
        while self.keepalive:
            sleep(1)
            with self.lock:
                self.progress.post_progress_with_time(connection)
                # requests.post(HOST_URL + "/worker/report_progress", data=)

    def __shutdown_keepalive(self) -> None:
        self.keepalive = False
        if self.keepalive_thread is not None:
            self.keepalive_thread.join()
        print("Shutting down worker message thread")
        self.receive_worker_messages = False

    def __stop_communication(self, communication_thread: threading.Thread) -> None:
        if self.log is None:
            self.save_log(crash=True)
        print("Sending log to server...")

        self.publish_with_producer(type_="fail_task", extended_info={"log": self.log})
        self.__shutdown_keepalive()

        if communication_thread is not None:
            communication_thread.join()

    def __toggle_test_page_logging(self) -> None:
        self.log_file = NamedTemporaryFile()
        self.log = None
        self.log_file_handler = logging.FileHandler(self.log_file.name, encoding="utf-8")

        root_logger.addHandler(self.log_file_handler)

    def __start_testing_keepalive_thread(self, connection: Connection) -> None:
        self.keepalive_thread = threading.Thread(
            target=self.__post_keepalive,
            args=(connection,),
            name="Keepalive-Thread",
            daemon=True,
        )
        self.keepalive_thread.start()

    @staticmethod
    def __build_axe_test_list(project_info):
        return [
            test[4:] if test.startswith("axe_") else test
            for test in project_info["tests"]
            if not test.startswith("test")
        ]

    @staticmethod
    def __get_communication_providers(
        task_id, target: Callable, receive_messages
    ) -> Tuple[Queue, Connection, Connection.Producer, threading.Thread]:
        queue = Queue("testing_interim_results", routing_key="testing_interim_results")
        connection = Connection(settings.CELERY_BROKER_URL, heartbeat=30)
        producer = connection.Producer()
        worker_communication_thread = threading.Thread(
            target=target,
            args=(task_id, receive_messages),
            name="Worker Communication Thread",
            daemon=True,
        )
        worker_communication_thread.start()

        return queue, connection, producer, worker_communication_thread

    @staticmethod
    def __close_connection(connection: Connection, producer: Connection.Producer) -> None:
        print("CLOSE_CONNECTION")
        producer.close()
        connection.close()


class ProgressStateCapsule:
    def __init__(self, test_page_class, producer, queue):
        self.test_page_class = test_page_class
        self.producer = producer
        self.queue = queue
        self.reporting_progress = self.__init_test_progress(
            estimated_job_time=Task.objects.get(id=self.task_id).target_job.estimated_testing_time
        )

    def __getattr__(self, attr):
        try:
            return getattr(self.test_page_class, attr)
        except AttributeError as err:
            raise AttributeError(f"{err}\n{self.__class__.__name__} object has no attribute {attr}")

    def report_progress(self, progress_dict):
        update_case_solver = ProgressReportCaseUpdater(self, progress_dict)
        progress_events = [
            "overall_progress",
            "thread_count",
            "tasks_count",
            "tasks_complete",
            "running_task_completed",
            "thread_status",
            "additional_info",
            "thread_task_cancellable",
            "thread_test_name",
            "interim_test_result",
            "screenshots_for_test",
            "page_screenshot",
        ]

        with self.lock:
            progress_events = [event for event in progress_events if event in progress_dict]

            for event in progress_events:
                getattr(update_case_solver, event)()
                self.reporting_progress = update_case_solver.get_current_progress()

    def progress_uploading_to_server(self):
        self.save_log()

        self.report_progress({"overall_progress": "Dumping to JSON", "thread_count": 0})
        print("Dumping to JSON")
        result_data = dumps({"tests": [], "log": self.log})
        self.report_progress(
            {"overall_progress": "Uploading test result data to server", "thread_count": 0},
        )

        return result_data

    def post_progress_with_time(self, connection: Connection):
        connection.heartbeat_check()

        progress_with_time = deepcopy(self.reporting_progress)
        progress_with_time["threads"] = list()
        self.__update_progress_time_status_changed(progress_with_time)

        self.publish_with_producer(type_="interim", extended_info={"progress": dumps(progress_with_time)})

    def upload_test_screenshots(self, test):
        screenshots_to_upload = list()

        if test.status != "ERROR":
            screenshots_to_upload = self.__build_screenshots_to_upload(
                test.problematic_elements, test.name, screenshots_to_upload
            )

        self.__post_screenshot_results(screenshots_to_upload, test.name)

    def post_test_results(self, test):
        issues = list()
        checked_elements_source = ""

        if test.status != "ERROR":
            checked_elements_source = self.__build_elements_source(checked_elements_source, test.checked_elements)
            issues = self.__build_issues(test.problematic_elements, issues)

        run_times = test.run_times if hasattr(test, "run_times") else list()

        test_object = self.__get_test_object(test, checked_elements_source, issues, run_times)
        self.publish_with_producer(type_="interim_test_result", extended_info={"test": test_object})

    def post_screenshot_images(self, url, image):
        self.publish_with_producer(
            type_="page_screenshot",
            extended_info={
                "url": url,
                "image": image,
            },
        )

    def __update_progress_time_status_changed(self, progress_with_time):
        # * initialize percentage
        self.reporting_progress["percentage_complete"] = self.reporting_progress.get("percentage_complete", 0)
        self.reporting_progress["percentage_of_job_complete"] = self.reporting_progress.get(
            "percentage_of_job_complete", 0
        )
        sub_screenshot_statuses = (
            "Checking for existing screenshot",
            "Taking screenshot",
            "Saving screenshot",
        )

        for thread_id, thread_dict in self.reporting_progress["threads"].items():
            target = deepcopy(thread_dict)

            # * Running Time on frontend
            target["time_since_status_changed"] = int(self.get_running_time() - target["time_status_changed"])

            if thread_dict.get("estimated_time") and not (
                thread_dict.get("additional_info")
                and any(thread_dict.get("additional_info").startswith(info) for info in sub_screenshot_statuses)
            ):
                # * disable time_since_status_changed for screenshot subtasks percentage_complete
                self.reporting_progress["percentage_complete"] = min(
                    99, round(target["time_since_status_changed"] / thread_dict["estimated_time"] * 100)
                )

            self.reporting_progress["percentage_of_job_complete"] = min(
                99,
                round(
                    self.reporting_progress["tasks_complete"] / self.reporting_progress["tasks_count"] * 100
                    + target["time_since_status_changed"]
                    / self.reporting_progress["estimated_time_of_all_tasks"]
                    * 100
                ),
            )

            progress_with_time["threads"].append(target)

    def __post_screenshot_results(self, screenshots_to_upload, test_name):
        for screenshot_id, screenshot_to_upload in enumerate(screenshots_to_upload):
            self.report_progress(
                {
                    "overall_progress": f"Uploading screenshot {screenshot_id + 1}/{len(screenshots_to_upload)} for {test_name} to server"
                }
            )
            print(f"Uploading screenshot {screenshot_id + 1}/{len(screenshots_to_upload)} to server")
            screenshot_data = dumps(screenshot_to_upload)

            self.publish_with_producer(type_="screenshot", extended_info={"screenshot_data": screenshot_data})

        self.report_progress({"overall_progress": "Running parallel tasks"})

    @staticmethod
    def __init_test_progress(estimated_job_time=0):
        return {
            "overall_progress": "Preparing the testing framework",
            "thread_count": 0,
            "threads": {},
            "tasks_complete": 0,
            "tasks_count": 1,
            "estimated_time_of_all_tasks": estimated_job_time,  # ! dup estimated_testing_time
        }

    @staticmethod
    def __get_test_object(test, checked_elements_source, issues, run_times):
        return {
            "name": test.name,
            "human_name": test.human_name,
            "WCAG": test.WCAG,
            "status": test.status,
            "issues": issues,
            "checked_elements": checked_elements_source,
            "support_status": "TEST",
            "problematic_pages": ";".join(test.problematic_pages),
            "run_times": run_times,
        }

    @staticmethod
    def __build_elements_source(elements_source, checked_elements):
        for index, element in enumerate(checked_elements):
            elements_source += (
                str(index + 1)
                + ") "
                + "Selector:"
                + str(element.selector)
                + " Snippet: "
                + str(element.source)
                + "\n"
            )

        return elements_source

    @staticmethod
    def __get_issue(problematic_element, code_snippet, severity):
        return {
            "err_id": problematic_element["error_id"],
            "code_snippet": code_snippet,
            "problematic_element_selector": problematic_element["element"].selector_no_id,
            "problematic_element_position": problematic_element["element"].position,
            "severity": severity,
            "pages": problematic_element["pages"],
            "uuid": problematic_element["uuid"],
            "important_example": problematic_element["important_example"],
            "force_best_practice": problematic_element["force_best_practice"]
            if "force_best_practice" in problematic_element
            else False,
            "page_resolution": problematic_element.get("page_resolution"),
        }

    @staticmethod
    def __build_issues(problematic_elements, issues):
        for problematic_element in problematic_elements:
            if len(problematic_element["element"].source) < 500:
                code_snippet = problematic_element["element"].source
            else:
                code_snippet = sub(r""">.*<""", ">...<", problematic_element["element"].source, flags=DOTALL)
                # Sometimes a single html tag is HUGE, in which case forcibly cut off the snippet
                if len(code_snippet) > 2000:
                    code_snippet = code_snippet[:2000] + "..."

            severity = problematic_element.get("severity", "FAIL")

            issue = ProgressStateCapsule.__get_issue(problematic_element, code_snippet, severity)
            issues.append(issue)

        return issues

    @staticmethod
    def __build_screenshots_to_upload(problematic_elements, test_name, screenshots_to_upload: List[dict]):
        for problematic_element in problematic_elements:
            if "screenshot" in problematic_element:
                with open(problematic_element["screenshot"], mode="rb") as screenshot:
                    screenshot_to_upload = dict()
                    screenshot_to_upload["uuid"] = problematic_element["uuid"]
                    screenshot_to_upload["test_name"] = test_name
                    screenshot_to_upload["screenshot"] = base64.b64encode(screenshot.read()).decode("ascii")

                    screenshots_to_upload.append(screenshot_to_upload)
            else:
                print(f"WARNING: Np screenshot for element {problematic_element['element'].source[:100]}")

        return screenshots_to_upload


class ProgressReportCaseUpdater:
    def __init__(self, progress_report_class, running_progress):
        self.progress_report_class = progress_report_class
        self.running_progress = running_progress

    def __getattr__(self, attr):
        try:
            return getattr(self.progress_report_class, attr)
        except AttributeError as err:
            raise AttributeError(f"{err}\n{self.__class__.__name__} object has no attribute {attr}")

    def get_current_progress(self):
        return self.reporting_progress

    def overall_progress(self):
        self.reporting_progress["overall_progress"] = self.running_progress["overall_progress"]

    def thread_count(self):
        self.reporting_progress["thread_count"] = self.running_progress["thread_count"]

        for thread_id in list(self.reporting_progress["threads"].keys()):
            if thread_id >= self.running_progress["thread_count"]:
                del self.reporting_progress["threads"][thread_id]

    def tasks_count(self):
        self.reporting_progress["tasks_count"] = self.running_progress["tasks_count"]

    def running_task_completed(self):
        for thread_id, thread_status_ in self.running_progress["thread_status"].items():
            thread_dict = self.__get_thread_dict(thread_id, self.reporting_progress, self.get_running_time())

            # * check run once for every test
            if thread_status_ != thread_dict["status"]:
                self.__set_test_queue_estimated_timings(thread_dict, thread_status_)
                # * self.reporting_progress updated with estimated_time

    def tasks_complete(self):
        self.reporting_progress["tasks_complete"] = self.running_progress["tasks_complete"]
        # * calculate here percentage of job in total
        # * reset percentage_of_job_complete from progress_with_time according to completed tasks
        self.reporting_progress["percentage_of_job_complete"] = round(
            self.reporting_progress["tasks_complete"] / self.reporting_progress["tasks_count"] * 100
        )

        # * test_percentage_complete = 100% - current task completed
        self.reporting_progress["percentage_complete"] = 100

    def thread_status(self):
        for thread_id, thread_status_ in self.running_progress["thread_status"].items():
            thread_dict = self.__get_thread_dict(thread_id, self.reporting_progress, self.get_running_time())

            if thread_status_ != thread_dict["status"]:
                _ = thread_dict["time_status_changed"]
                thread_dict["status"] = thread_status_
                thread_dict["time_status_changed"] = self.get_running_time()
                thread_dict["additional_info"] = None

    def additional_info(self):
        for thread_id, additional_info in self.running_progress["additional_info"].items():
            thread_dict = self.__get_thread_dict(thread_id, self.reporting_progress, self.get_running_time())
            if additional_info != thread_dict["additional_info"]:
                thread_dict["additional_info"] = additional_info
                thread_dict["time_status_changed"] = self.get_running_time()

    def thread_task_cancellable(self):
        for thread_id, task_cancellable in self.running_progress["thread_task_cancellable"].items():
            self.__get_thread_dict(thread_id, self.reporting_progress, self.get_running_time())[
                "task_cancellable"
            ] = task_cancellable

    def thread_test_name(self):
        for thread_id, task_cancellable in self.running_progress["thread_test_name"].items():
            self.__get_thread_dict(thread_id, self.reporting_progress, self.get_running_time())[
                "test_name"
            ] = task_cancellable

    def interim_test_result(self):
        test = self.running_progress["interim_test_result"]
        print(f"Received interim results: {test.status} - {test.name}")
        self.post_test_results(test)

    def screenshots_for_test(self):
        test = self.running_progress["screenshots_for_test"]
        print(f"Received screenshots for {test.name}")
        self.upload_test_screenshots(test)

    def page_screenshot(self):
        url = self.running_progress["page_screenshot"]["url"]
        image = self.running_progress["page_screenshot"]["image"]
        image = base64.b64encode(image).decode("ascii")
        self.post_screenshot_images(url, image)

    def __set_test_queue_estimated_timings(self, running_thread_dict, running_thread_status):
        test_task_name = running_thread_status.lstrip("Running ")
        # * generator next, update running_task_name
        timing_data = self.test_timings.send(test_task_name)

        running_thread_dict["estimated_time"] = timing_data["time"]

    @staticmethod
    def __get_thread_dict(thread_id, progress_dict, running_time):
        # * implicit update of self.reporting_progress
        if thread_id not in progress_dict["threads"]:
            progress_dict["threads"][thread_id] = {
                "id": thread_id,
                "status": "Starting...",
                "time_status_changed": running_time,
                "task_cancellable": False,
                "test_name": None,
                "additional_info": None,
            }

        return progress_dict["threads"][thread_id]


class WorkerMessagesCapsule:
    def __init__(self, task_id):
        self.task_id = task_id
        self.cancelled_tests = []

    def receive_worker_communication_messages(self, task_id, should_receive_worker_messages: bool):
        with Connection(settings.CELERY_BROKER_URL, heartbeat=30) as inbound_connection:
            worker_communication_queue = Queue(
                exchange=Exchange("worker_communication"),
                routing_key="worker_communication",
                # Ensures that this dynamically created queue gets cleaned up
                auto_delete=True,
            )
            consumer = inbound_connection.Consumer(worker_communication_queue)
            # # Create this unique queue, since it was not declared by the producer
            # consumer.declare()

            consumer.register_callback(self.__receive_worker_message)
            with consumer:
                while should_receive_worker_messages:
                    try:
                        inbound_connection.drain_events(timeout=1)
                    except timeout:
                        # print("No messages for 5 seconds")
                        pass
                    inbound_connection.heartbeat_check()

    def __receive_worker_message(self, body, message):
        message.ack()
        if int(body["task_id"]) == self.task_id:
            if body["test_name"] in self.cancelled_tests:
                print(f"Ignoring cancel command for already cancelled test {body['test_name']}")
            else:
                print(f"Force cancelling test {body['test_name']}")
                self.cancelled_tests.append(body["test_name"])
        else:
            print(f"Ignoring cancel message for task {body['task_id']}, we are running task {self.task_id}")
