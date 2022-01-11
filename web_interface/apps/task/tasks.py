import base64
import datetime
import json
import logging
import os
import re
import tempfile
import threading
import time
import traceback
import uuid
from copy import deepcopy
from itertools import chain
from socket import timeout
from typing import Optional, Collection, Union

import requests
from celery import shared_task
from celery.result import AsyncResult
from dateutil.relativedelta import *
from django.conf import settings
from django.core.cache import cache
from django.db.models import Subquery
from kombu import Queue, Connection, Exchange
from lxml import html
from requests.adapters import HTTPAdapter, Retry
from selenium import webdriver

from framework import activity, time_estimator, xlsdata
from framework.main import discover_and_run
from framework.tools.sitemap import SiteMap
from web_interface.apps.activity.models import Activity
from web_interface.apps.framework_data.models import AvailableTest, TestTiming, Test, TestResults
from web_interface.apps.issue import example_manipulation
from web_interface.apps.issue.models import PageScreenshot, Example, ExampleScreenshot
from web_interface.apps.jira.models import JiraWorkerTask, JiraIntegrationParams
from web_interface.apps.job.models import Job
from web_interface.apps.page.models import Page
from web_interface.apps.project.models import Project
from web_interface.apps.report import report_generator
from web_interface.apps.report.models import Issue, SuccessCriteriaLevel, ConformanceLevel
from web_interface.apps.task import api_token
from web_interface.apps.task.models import Report
from web_interface.apps.task.models import Task, SitemapTask
from web_interface.apps.task_planner.models import PlannedTask
from web_interface.backend.conformance import (
    fill_508,
    update_conformance_level,
    update_success_criteria_level,
    update_level_for_section_chapter,
)
from web_interface.backend.jira.JiraIntegration import JiraIntegration
from web_interface.celery import control

SITEMAP_QUOTA = 2

root_logger = logging.getLogger("framework")
root_logger.setLevel(logging.DEBUG)
root_logger.propagate = False

console_out = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] (%(threadName)s) %(name)s/%(levelname)s:%(message)s")
console_out.setFormatter(formatter)
root_logger.addHandler(console_out)

if "USE_DOCKER" in os.environ:
    HOST_URL = "http://nginx:80"
else:
    HOST_URL = "http://localhost:8000"

WEEKDAYS = {0: MO, 1: TU, 2: WE, 3: TH, 4: FR, 5: SA, 6: SU}


def task_fail(self, exc, task_id, args, kwargs, einfo) -> None:
    worker_key = kwargs.get("worker_key")
    task_id = kwargs.get("task_id")
    requests.post(HOST_URL + "/worker/fail_task", data={"worker_key": worker_key, "task_id": task_id})


def is_sitemap_running(project_id) -> bool:
    # selected_project_sitemap_deleted = _verify_sitemap_tasks(project_id)
    # if selected_project_sitemap_deleted:
    #     return False
    try:
        task = SitemapTask.objects.get(project_id=project_id)
    except SitemapTask.DoesNotExist:
        return False

    result = AsyncResult(task.celery_task_id)
    if result.ready():
        print(f"Sitemap Task {task.celery_task_id} for Project({project_id}) ready. Deleting SitemapTask ...")
        task.delete()
        return False
    return True


def get_remaining_sitemap_quota() -> int:
    return SITEMAP_QUOTA - SitemapTask.objects.filter(status=SitemapTask.RUNNING).count()


def _verify_sitemap_tasks(selected_project_id):
    if cache.get("sitemap_task_verified") is None:
        cache.set("sitemap_task_verified", time.time(), 60)

        selected_was_deleted = False
        active_task_ids = _get_active_task_ids()
        for task in SitemapTask.objects.exclude(celery_task_id__in=active_task_ids):
            task_project_id = task.project_id
            print(
                f"Sitemap Task {task.celery_task_id} for Project({task_project_id}) "
                f"present in DB but not in Celery, removing"
            )
            task.delete()
            if task_project_id == selected_project_id:
                selected_was_deleted = True
        return selected_was_deleted
    return False


def _get_active_task_ids():
    task_ids = []
    all_task_list = []
    all_task_list.extend(control.inspect().active().values())
    all_task_list.extend(control.inspect().reserved().values())
    all_task_list.extend(control.inspect().scheduled().values())
    for task in chain.from_iterable(all_task_list):
        if "id" in task:
            task_ids.append(task["id"])
        else:
            task_ids.append(task["request"]["id"])
    print(f"Updated task ids: {task_ids}")
    return task_ids


@shared_task(queue="shortlived")
def verify_tasks_running():
    return
    # if cache.get("test_task_verified") is None:
    #     cache.set("test_task_verified", time.time(), 60)
    #     task_list = Task.objects.filter(Q(status=Task.RUNNING) | Q(status=Task.QUEUED))
    #     active_task_ids = _get_active_task_ids()
    #     cached_to_remove = cache.get("tasks_to_remove") or list()
    #     tasks_to_remove = list()
    #     for task in task_list:
    #         if task.celery_task_id not in active_task_ids:
    #             if task.celery_task_id in cached_to_remove:
    #                 task.status = task.CRASHED
    #                 print(f"Task {task.celery_task_id} missing in Celery but present in DB, setting as crashed")
    #                 task.message = "Task missing in Celery but present in DB"
    #                 task.save()
    #             else:
    #                 tasks_to_remove.append(task.celery_task_id)
    #     cache.set("tasks_to_remove", tasks_to_remove, 120)


def request_test_for_job(job):
    print("Requesting test for " + str(job.id))

    if Task.objects.filter(target_job=job, status__in=(Task.QUEUED, Task.RUNNING)).exists():
        print(f"Task for {str(job.id)} already running")
        return {"task_id": -1, "status": "already_running", "celery_task_id": ""}

    test_list = job.test_list.split(",")
    pages = job.pages.select_related("project")
    project = job.project
    options = project.options
    page_infos = list()
    for page in pages:
        activities = [
            {
                "name": activity.name,
                "side_file": activity.side_file.read().decode("utf-8") if activity.side_file else "",
                "element_click_order": activity.click_sequence.split(";")
                if activity.click_sequence is not None
                else None,
            }
            for activity in Activity.objects.filter(page=page)
        ]
        if len(activities) == 0:
            page_info = {
                "url": page.url,
                "options": options,
                "name": page.name,
                "page_after_login": page.project.page_after_login,
            }
        else:
            page_info = {
                "url": page.url,
                "activities": activities,
                "options": options,
                "name": page.name,
                "page_after_login": page.project.page_after_login,
            }
        page_infos.append(page_info)

    task = Task.objects.create(
        date_started=datetime.datetime.now(datetime.timezone.utc), target_job=job, status=Task.QUEUED, message=""
    )

    job.last_test = task.date_started
    job.save()
    job.project.last_test = task.date_started
    job.project.save()

    token = api_token.create_worker_key(task)

    vpat_reports = ""
    audit_reports = ""

    project_info = {
        "page_infos": page_infos,
        "tests": test_list,
        "name": project.name,
        "comment": project.comment,
        "date_created": str(project.created_stamp),
        "version": project.version,
        "contact": project.contact,
        "company": project.company,
        "vpat_reports": vpat_reports,
        "audit_reports": audit_reports,
        "request_interval": project.request_interval,
        "enable_content_blocking": project.enable_content_blocking,
        "enable_popup_detection": project.enable_popup_detection,
        "no_parallel_login": project.disable_parallel_testing,
    }
    result = test_page.delay(project_info=project_info, task_id=task.id, worker_key=token)
    # check_if_task_alive.apply_async((task.id,), countdown=60)
    task.celery_task_id = result.id
    task.save()
    return {"task_id": task.id, "status": "ok", "celery_task_id": result.id}


@shared_task(queue="shortlived")
def check_if_task_alive(task_id):
    task = Task.objects.get(id=task_id)
    print(f"Watching task {task.celery_task_id}")
    if task.status == Task.RUNNING or task.status == Task.QUEUED:
        if (
            task.status == Task.RUNNING
            and (datetime.datetime.now(datetime.timezone.utc) - task.last_reported).total_seconds() > 60
        ):
            print(f"Task {task.celery_task_id} timed out, force terminating")
            control.revoke(task.celery_task_id, terminate=True)
            # Schedule a force kill if does not shut down in 10s
            kill_task.apply_async((task.celery_task_id,), countdown=10)
            task.status = Task.CRASHED
            task.message = "No response from worker for 60s"
            task.save()
        else:
            check_if_task_alive.apply_async((task_id,), countdown=60)
    else:
        print(f"Task {task.celery_task_id} finished")


def generate_sitemap(project_id, depth_level: Optional[int] = None) -> bool:
    if not is_sitemap_running(project_id) and get_remaining_sitemap_quota() > 0:
        project = Project.objects.get(id=project_id)

        # Revoking active tasks
        tasks_qs = Task.objects.filter(
            target_job_id__in=Subquery(project.jobs.values("id")),
            status__in=(Task.QUEUED, Task.RUNNING),
            is_valid=True,
        )
        for task in tasks_qs:
            abort_task(task)

        # Removing all previous pages
        project.pages.all().delete()
        result = process_sitemap.delay(project_id, depth_level)
        SitemapTask.objects.create(
            project_id=project_id, celery_task_id=result.task_id, status=SitemapTask.RUNNING
        )
        return True
    else:
        return False


@shared_task(queue="shortlived")
def update_page_size(page_id):
    page = Page.objects.get(id=page_id)
    page_size_info = time_estimator.get_page_size(page.url)
    page.page_size_data = json.dumps(page_size_info)
    page.save()
    return True


def update_test_time_data():
    with open(r"framework/time_of_tests/average_time.json", "r", encoding="utf-8") as f:
        time_data_default = json.load(f)
    for test in AvailableTest.objects.all():
        time_data = dict()
        time_stats = TestTiming.objects.filter(name=test.name)
        if time_stats:
            time_data["time_constant"] = 1
            times_per_elements = list()
            for stat in time_stats:
                if stat.page_size_data:
                    page_size_data = json.loads(stat.page_size_data)
                    time_per_elements = stat.run_times / page_size_data["all_elements_count"]
                    times_per_elements.append(time_per_elements)
            if times_per_elements:
                time_data["time_per_element"] = sum(times_per_elements) / len(times_per_elements)
            else:
                time_data["time_per_element"] = 0.01
        else:
            if test.name in time_data_default:
                time_data["time_constant"] = time_data_default[test.name]
                time_data["time_per_element"] = 0
            else:
                continue
        time_data_dump = json.dumps(time_data)
        test.time_data = time_data_dump
        test.save()
    print("updated_test_time_data")


def get_test_time_data():
    test_time_data = dict()
    for test in AvailableTest.objects.all():
        if test.time_data is not None:
            test_time_data[test.name] = json.loads(test.time_data)
    return test_time_data


def get_page_size_data(page):
    if page.page_size_data is None:
        page_size_data = {
            "page_load_time": 10,
            "all_elements_count": 1000,
            "a": 50,
            "img": 5,
            "button": 10,
            "input": 4,
            "form": 1,
            "table": 0,
            "div": 500,
            "span": 100,
        }
    else:
        page_size_data = json.loads(page.page_size_data)
    page_size_data["name"] = page.name
    page_size_data["activity_count"] = Activity.objects.filter(page=page).count()
    if page_size_data["activity_count"] == 0:
        page_size_data["activity_count"] = 1
    return page_size_data


def precalculate_job_length(tests, pages):
    page_data = []
    for page_id in pages:
        page = Page.objects.get(id=int(page_id))
        page_data.append(get_page_size_data(page))

    test_time_data = get_test_time_data()
    test_list = tests
    estimated_testing_time = time_estimator.simulate_testing(test_list, page_data, test_time_data)
    return estimated_testing_time + 120  # default time for load and destroy (temporary)


@shared_task(queue="shortlived")
def update_job_length(job_id):
    job = Job.objects.get(id=job_id)

    test_time_data = get_test_time_data()

    page_data = list()
    for page in job.pages.all():
        page_data.append(get_page_size_data(page))

    test_list = job.test_list.split(",")
    estimated_testing_time = time_estimator.simulate_testing(test_list, page_data, test_time_data)
    job.estimated_testing_time = estimated_testing_time + 120  # default time for load and destroy (temporary)
    job.save()


@shared_task(queue="shortlived_realtime")
def process_sitemap(project_id, depth_level: Optional[int] = None):
    project = Project.objects.get(id=project_id)

    if json.loads(project.options)["auth_required"]:
        mode = "auth"
    else:
        mode = "simple"

    sitemap = SiteMap(project.url, mode, options=project.options, depth_level=depth_level)
    sitemap.get_sitemap()
    local_pages = []
    for counter, item in enumerate(sitemap.sitemap):
        print(f"Retrieving title information for page {counter+1}/{len(sitemap.sitemap)}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0",
            }
            response = requests.get(item["url"], headers=headers)
            response.encoding = "utf-8"
            if response.status_code == 502:
                response = requests_retry_session(retries=2).get(item["url"], headers=headers)
            parsed_body = html.fromstring(response.text)
            title = parsed_body.xpath("//title/text()")[0]
            print(title)
            if "404" in title:
                continue
        except:
            title = item["url"]
        local_page = Page(name=title, url=item["url"], project=project)
        local_page.parent_url = item["parent"]
        local_pages.append(local_page)

    batch_size = 64
    populated_pages = Page.objects.bulk_create(local_pages, batch_size=batch_size)
    for page in populated_pages:
        best_parent = None
        for potential_parent in populated_pages:
            if potential_parent == page:
                continue
            if page.url.startswith(potential_parent.url):
                if best_parent is None or len(potential_parent.url) > len(best_parent.url):
                    best_parent = potential_parent
        if best_parent:
            page.parent_page = best_parent

    Page.objects.bulk_update(populated_pages, ["parent_page"], batch_size=batch_size)
    sitemap_task = SitemapTask.objects.get(project=project)
    sitemap_task.status = sitemap.status
    sitemap_task.message = sitemap.message
    sitemap_task.save()

    for page_id in map(lambda pg: pg.id, populated_pages):
        update_page_size.delay(page_id)

    print("Sitemap processed, pages created")


def requests_retry_session(
    retries: Optional[Union[bool, int]] = 3,
    backoff_factor: float = 0.3,
    status_forcelist: Optional[Collection[int]] = (502,),
    session: Optional[requests.Session] = None,
) -> requests.Session:
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def is_activity_running(activity_id) -> dict:
    result = AsyncResult(activity_id)
    if result.ready():
        return {"running": False, "status": result.state, "result": result.result}
    return {"running": True, "status": result.state, "result": result.result}


def verify_activity(activity_info):
    webdriver_instance = webdriver.Firefox()
    webdriver_instance.maximize_window()
    activities = [
        {
            "name": activity_info.name,
            "side_file": activity_info.side_file.read().decode("utf-8") if activity_info.side_file else "",
            "element_click_order": activity_info.click_sequence.split(";")
            if activity_info.click_sequence is not None
            else None,
        }
    ]

    page_info = {
        "url": activity_info.page.url,
        "options": activity_info.page.project.options,
        "name": activity_info.page.name,
        "page_after_login": activity_info.page.project.page_after_login,
        "activities": activities,
    }

    try:
        driver = webdriver.Firefox()
        activities = activity.load_activities(page_info, driver)
        activities[0].get(driver)
    except Exception as e:
        return False, f"Failed to open activity: {e}"

    return True, "Activity validated"


@shared_task(queue="shortlived")
def kill_task(celery_task_id) -> None:
    print(f"Force killing task {celery_task_id}")
    control.revoke(celery_task_id, terminate=True, signal="SIGKILL")


def regenerate_report(task, delta_starting_task):
    if (
        Report.objects.filter(
            task=task, delta_starting_task=delta_starting_task, status__in=[Report.GENERATING, Report.QUEUED]
        ).count()
        > 0
    ):
        print("Report already queued for this task!")
        return False

    report = Report.objects.create(task=task, delta_starting_task=delta_starting_task, status=Report.QUEUED)
    task.save()
    generate_report.delay(report.id)
    print(f"Queued report regeneration for task {task}")


@shared_task(queue="shortlived")
def generate_report(report_id):
    report = Report.objects.get(id=report_id)
    report.status = Report.GENERATING
    report.save()

    task = report.task
    name = task.target_job.project.name + " " + task.target_job.name
    extension = ".docx"
    filename = f"{name}_{task.date_started}{extension}"
    filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)
    print(f"Generating report {filename}...")
    report.generated_report.save(filename, report_generator.generate_report(task, report.delta_starting_task))
    report.status = Report.SUCCESS
    report.save()
    print(f"Report generated!")


def abort_task(task: Task) -> None:
    control.revoke(task.celery_task_id, terminate=True)
    # Schedule a force kill if does not shut down in 10s
    kill_task.apply_async((task.celery_task_id,), countdown=10)
    task.status = Task.ABORTED
    task.save()


def cancel_test_for_task(task_id, test_name):
    exchange = Exchange("worker_communication")
    print(f"Cancelling test {test_name} for task {task_id}")
    with Connection(settings.CELERY_BROKER_URL) as connection:
        producer = connection.Producer()
        producer.publish(
            {"task_id": task_id, "test_name": test_name},
            retry=True,
            exchange=exchange,
            routing_key="worker_communication",
            declare=[exchange],
        )


@shared_task(bind=True, on_failure=task_fail, queue="longlived")
def test_page(self, project_info, task_id, worker_key):
    log = None
    keepalive_thread = None
    log_file = tempfile.NamedTemporaryFile()
    log_file_handler = logging.FileHandler(log_file.name, encoding="utf-8")
    root_logger.addHandler(log_file_handler)
    queue = Queue("testing_interim_results", routing_key="testing_interim_results")
    connection = Connection(settings.CELERY_BROKER_URL, heartbeat=30)
    producer = connection.Producer()
    rabbitmq_outbound_lock = threading.Lock()
    cancelled_tests = list()

    # Prepare to receive cancelled test messages
    should_receive_worker_messages = True

    def receive_worker_communication_messages():
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

            def receive_worker_message(body, message):
                message.ack()
                if int(body["task_id"]) == task_id:
                    if body["test_name"] in cancelled_tests:
                        print(f"Ignoring cancel command for already cancelled test {body['test_name']}")
                    else:
                        print(f"Force cancelling test {body['test_name']}")
                        cancelled_tests.append(body["test_name"])
                else:
                    print(f"Ignoring cancel message for task {body['task_id']}, we are runnning task {task_id}")

            consumer.register_callback(receive_worker_message)
            with consumer:
                while should_receive_worker_messages:
                    try:
                        inbound_connection.drain_events(timeout=1)
                    except timeout:
                        # print("No messages for 5 seconds")
                        pass
                    inbound_connection.heartbeat_check()

    worker_communication_thread = threading.Thread(
        target=receive_worker_communication_messages, name="Worker Communication Thread", daemon=True
    )

    worker_communication_thread.start()

    try:
        with rabbitmq_outbound_lock:
            producer.publish(
                {
                    "worker_key": worker_key,
                    "type": "set_running",
                    "task_id": task_id,
                    "celery_task_id": self.request.id,
                },
                retry=True,
                exchange=queue.exchange,
                routing_key=queue.routing_key,
                declare=[queue],
            )

        cur_progress = {
            "overall_progress": "Preparing the testing framework",
            "thread_count": 0,
            "threads": {},
            "tasks_complete": 0,
            "tasks_count": 1,
        }

        lock = threading.RLock()
        keepalive = True

        # elements_with_screenshots = 0
        # elements_without_screenshots = 0

        def post_test_results(test):
            issues = list()
            checked_elements_source = ""
            if test.status != "ERROR":
                for index, element in enumerate(test.checked_elements):
                    checked_elements_source += (
                        str(index + 1)
                        + ") "
                        + "Selector:"
                        + str(element.selector)
                        + " Snippet: "
                        + str(element.source)
                        + "\n"
                    )
                for problematic_element in test.problematic_elements:
                    if len(problematic_element["element"].source) < 500:
                        code_snippet = problematic_element["element"].source
                    else:
                        code_snippet = re.sub(
                            r""">.*<""", ">...<", problematic_element["element"].source, flags=re.DOTALL
                        )
                        # Sometimes a single html tag is HUGE, in which case forcibly cut off the snippet
                        if len(code_snippet) > 2000:
                            code_snippet = code_snippet[:2000] + "..."
                    try:
                        severity = problematic_element["severity"]
                    except KeyError:
                        severity = "FAIL"
                    issue = {
                        "err_id": problematic_element["error_id"],
                        "code_snippet": code_snippet,
                        "problematic_element_selector": problematic_element["element"].selector_no_id,
                        "problematic_element_position": problematic_element["element"].position,
                        "severity": severity,
                        "pages": problematic_element["pages"],
                        "uuid": problematic_element["uuid"],
                        "force_best_practice": problematic_element["force_best_practice"]
                        if "force_best_practice" in problematic_element
                        else False,
                    }
                    # if "screenshot" in problematic_element:
                    #     with open(problematic_element["screenshot"], mode="rb") as screenshot:
                    #         screenshot_to_upload = dict()
                    #         screenshot_to_upload["issue_number_in_task"] = number_in_task
                    #         screenshot_to_upload["screenshot"] = base64.b64encode(screenshot.read()).decode('ascii')
                    #         screenshots_to_upload.append(screenshot_to_upload)
                    #     elements_with_screenshots += 1
                    # else:
                    #     elements_without_screenshots += 1
                    issues.append(issue)
                    # number_in_task += 1
            run_times = list()
            try:
                run_times = test.run_times
            except Exception:
                pass
            test_object = {
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
            with rabbitmq_outbound_lock:
                producer.publish(
                    {
                        "worker_key": worker_key,
                        "type": "interim_test_result",
                        "task_id": task_id,
                        "test": test_object,
                    },
                    retry=True,
                    exchange=queue.exchange,
                    routing_key=queue.routing_key,
                    declare=[queue],
                )

        def upload_test_screenshots(test):
            screenshots_to_upload = list()
            if test.status != "ERROR":
                for problematic_element in test.problematic_elements:
                    if "screenshot" in problematic_element:
                        with open(problematic_element["screenshot"], mode="rb") as screenshot:
                            screenshot_to_upload = dict()
                            screenshot_to_upload["uuid"] = problematic_element["uuid"]
                            screenshot_to_upload["test_name"] = test.name
                            screenshot_to_upload["screenshot"] = base64.b64encode(screenshot.read()).decode(
                                "ascii"
                            )
                            screenshots_to_upload.append(screenshot_to_upload)
                    else:
                        print(f"WARNING: Np screenshot for element {problematic_element['element'].source[:100]}")
            with rabbitmq_outbound_lock:
                for screenshot_id, screenshot_to_upload in enumerate(screenshots_to_upload):
                    report_progress(
                        {
                            "overall_progress": f"Uploading screenshot {screenshot_id + 1}/{len(screenshots_to_upload)} for {test.name} to server"
                        }
                    )
                    print(f"Uploading screenshot {screenshot_id + 1}/{len(screenshots_to_upload)} to server")
                    screenshot_data = json.dumps(screenshot_to_upload)
                    producer.publish(
                        {
                            "worker_key": worker_key,
                            "type": "screenshot",
                            "task_id": task_id,
                            "screenshot_data": screenshot_data,
                        },
                        retry=True,
                        exchange=queue.exchange,
                        routing_key=queue.routing_key,
                        declare=[queue],
                    )
                report_progress({"overall_progress": f"Running parallel tasks"})

        def get_thread_dict(thread_id):
            if thread_id not in cur_progress["threads"]:
                cur_progress["threads"][thread_id] = {
                    "id": thread_id,
                    "status": "Starting...",
                    "time_status_changed": time.time(),
                    "task_cancellable": False,
                    "test_name": None,
                    "additional_info": None,
                }
            return cur_progress["threads"][thread_id]

        def report_progress(progress):
            with lock:
                if "overall_progress" in progress:
                    cur_progress["overall_progress"] = progress["overall_progress"]
                if "thread_count" in progress:
                    cur_progress["thread_count"] = progress["thread_count"]
                    for thread_id in list(cur_progress["threads"].keys()):
                        if thread_id >= progress["thread_count"]:
                            del cur_progress["threads"][thread_id]
                if "tasks_count" in progress:
                    cur_progress["tasks_count"] = progress["tasks_count"]
                if "tasks_complete" in progress:
                    cur_progress["tasks_complete"] = progress["tasks_complete"]
                if "thread_status" in progress:
                    for thread_id, thread_status in progress["thread_status"].items():
                        thread_dict = get_thread_dict(thread_id)
                        if thread_status != thread_dict["status"]:
                            thread_dict["status"] = thread_status
                            thread_dict["time_status_changed"] = time.time()
                            thread_dict["additional_info"] = None
                if "additional_info" in progress:
                    for thread_id, additional_info in progress["additional_info"].items():
                        thread_dict = get_thread_dict(thread_id)
                        if additional_info != thread_dict["additional_info"]:
                            thread_dict["additional_info"] = additional_info
                            thread_dict["time_status_changed"] = time.time()
                if "thread_task_cancellable" in progress:
                    for thread_id, task_cancellable in progress["thread_task_cancellable"].items():
                        get_thread_dict(thread_id)["task_cancellable"] = task_cancellable
                if "thread_test_name" in progress:
                    for thread_id, task_cancellable in progress["thread_test_name"].items():
                        get_thread_dict(thread_id)["test_name"] = task_cancellable
                if "interim_test_result" in progress:
                    test = progress["interim_test_result"]
                    print(f"Received interim results: {test.status} - {test.name}")
                    post_test_results(test)
                if "screenshots_for_test" in progress:
                    test = progress["screenshots_for_test"]
                    print(f"Received screenshots for {test.name}")
                    upload_test_screenshots(test)
                if "page_screenshot" in progress:
                    url = progress["page_screenshot"]["url"]
                    image = progress["page_screenshot"]["image"]
                    image = base64.b64encode(image).decode("ascii")
                    with rabbitmq_outbound_lock:
                        producer.publish(
                            {
                                "worker_key": worker_key,
                                "type": "page_screenshot",
                                "task_id": task_id,
                                "url": url,
                                "image": image,
                            },
                            exchange=queue.exchange,
                            routing_key=queue.routing_key,
                            declare=[queue],
                        )

        def post_keepalive():
            while keepalive:
                time.sleep(1)
                with lock:
                    with rabbitmq_outbound_lock:
                        connection.heartbeat_check()
                        progress_with_time = deepcopy(cur_progress)
                        progress_with_time["threads"] = list()
                        for thread_id, thread_dict in cur_progress["threads"].items():
                            target = deepcopy(thread_dict)
                            target["time_since_status_changed"] = int(time.time() - target["time_status_changed"])
                            progress_with_time["threads"].append(target)

                        producer.publish(
                            {
                                "worker_key": worker_key,
                                "type": "interim",
                                "task_id": task_id,
                                "progress": json.dumps(progress_with_time),
                            },
                            exchange=queue.exchange,
                            routing_key=queue.routing_key,
                            declare=[queue],
                        )
                    # requests.post(HOST_URL + "/worker/report_progress", data=)

        keepalive_thread = threading.Thread(target=post_keepalive, name="Keepalive-Thread", daemon=True)

        keepalive_thread.start()

        project_info["task_id"] = self.request.id

        axe_test_list = [
            test[4:] if test.startswith("axe_") else test
            for test in project_info["tests"]
            if not test.startswith("test")
        ]
        tests = discover_and_run(
            project_info=project_info,
            filter_test=[test for test in project_info["tests"] if test.startswith("test")],
            run_axe_tests=axe_test_list,
            progress_report_callback=report_progress,
            cancelled_tests=cancelled_tests,
        )

        result = dict()

        result["tests"] = list()

        root_logger.removeHandler(log_file_handler)
        log_file.seek(0)
        log = log_file.read().decode(encoding="utf-8")
        log_file.close()

        result["log"] = log
        # print(f"Elements with screenshots {elements_with_screenshots}. without: {elements_without_screenshots}")
        report_progress({"overall_progress": f"Dumping to JSON", "thread_count": 0})
        print("Dumping to JSON")
        result_data = json.dumps(result)
        report_progress({"overall_progress": f"Uploading test result data to server", "thread_count": 0})
        print("Shutting down keepalive thread")
        keepalive = False
        keepalive_thread.join()
        print("Shutting down worker message thread")
        should_receive_worker_messages = False
        worker_communication_thread.join()
        print(f"Uploading data to server ({len(result_data) / 1000000} MB)")
        with rabbitmq_outbound_lock:
            producer.publish(
                {"worker_key": worker_key, "type": "results", "task_id": task_id, "result": result_data},
                retry=True,
                exchange=queue.exchange,
                routing_key=queue.routing_key,
                declare=[queue],
            )

        with rabbitmq_outbound_lock:
            producer.publish(
                {"worker_key": worker_key, "type": "finish", "task_id": task_id},
                retry=True,
                exchange=queue.exchange,
                routing_key=queue.routing_key,
                declare=[queue],
            )
        print("TASK FINISHED")

    except Exception:
        print("EXCEPTION WHILE RUNNING JOB")
        print(traceback.format_exc())
        print("Saving crash log...")
        if log is None:
            root_logger.removeHandler(log_file_handler)
            log_file.seek(0)
            log = log_file.read().decode(encoding="utf-8")
            log_file.close()
        print("Sending log to server...")
        with rabbitmq_outbound_lock:
            producer.publish(
                {"worker_key": worker_key, "type": "fail_task", "task_id": task_id, "log": log},
                retry=True,
                exchange=queue.exchange,
                routing_key=queue.routing_key,
                declare=[queue],
            )
        print("Shutting down keepalive thread")
        keepalive = False
        if keepalive_thread is not None:
            keepalive_thread.join()
        print("Shutting down worker message thread")
        should_receive_worker_messages = False
        if worker_communication_thread is not None:
            worker_communication_thread.join()
        print("TASK FAILED")
    producer.close()
    connection.close()


def receive_callback(body, message):
    msg_type = body["type"]
    key = body["worker_key"]
    task_id = body["task_id"]
    task = Task.objects.get(id=task_id)
    task.last_reported = datetime.datetime.now(datetime.timezone.utc)
    task.save()
    message.ack()
    if not api_token.check_worker_key(key, task):
        print("Request denied, invalid token!")
        return
    if msg_type == "interim":
        progress = body["progress"]
        task.progress = progress
        task.save()
    elif msg_type == "set_running":
        print(f"Setting task {task_id} status to RUNNING")
        task_status_before = task.status

        test_results = TestResults.objects.create()
        task.test_results = test_results
        task.save()
        if task_status_before != Task.ABORTED:
            task.status = Task.RUNNING
            task.last_reported = datetime.datetime.now(datetime.timezone.utc)
            task.celery_task_id = body["celery_task_id"]
            task.save()
    elif msg_type == "fail_task":
        print(f"Task {task_id} failed")
        if "message" in body:
            task.message = body["message"]
        task.status = Task.CRASHED
        if "log" in body:
            task.log = str(body["log"])
        else:
            task.log = "No log received from worker"
        task.save()

        api_token.delete_worker_key(key)
    elif msg_type == "interim_test_result":
        test = body["test"]

        print(f"Received interim test results for task {task_id}, test {test['name']}")

        test_results = task.test_results

        test_obj = Test.objects.create(
            name=test["name"],
            status=test["status"],
            support_status=test["support_status"],
            checked_elements=test["checked_elements"],
            test_results=test_results,
            problematic_pages=test["problematic_pages"],
        )
        for run_time in test["run_times"]:
            page_params = Page.objects.filter(url=run_time[0]).latest("id").page_size_data
            TestTiming.objects.create(name=test["name"], run_times=run_time[2], page_size_data=page_params)

        for issue in test["issues"]:
            err_id = issue["err_id"]
            orig_data = xlsdata.get_data_for_issue(err_id)
            issue_obj = Example.objects.create(
                err_id=err_id,
                code_snippet=issue["code_snippet"],
                problematic_element_selector=issue["problematic_element_selector"],
                problematic_element_position=issue["problematic_element_position"],
                test=test_obj,
                severity=issue["severity"],
                expected_result=orig_data["expected_result"],
                actual_result=orig_data["actual_result"],
                test_results=test_results,
                uuid=issue["uuid"],
                force_best_practice=issue["force_best_practice"],
            )
            print(f"Created issue with uuid {issue['uuid']}")
            # print(issue["pages"])
            issue_obj.pages.clear()

            for page in issue["pages"]:
                page_objects = Page.objects.filter(project=task.target_job.project, url=page)
                if len(page_objects) != 1:
                    print(f"Multiple pages with the same url {page} - cannot assign page to issue")
                    break
                # print(f"Adding page {page_obj.id} {page_obj.url}")
                issue_obj.pages.add(page_objects[0])
                print(f"Added page {page_objects[0].name}")
            issue_obj.save()

        example_manipulation.group_and_annotate(test_results)
    elif msg_type == "page_screenshot":
        test_results = task.test_results
        page_url = body["url"]
        image = body["image"]

        print(f"Received page screenshot for {page_url}")
        page_objects = Page.objects.filter(project=task.target_job.project, url=page_url)
        if len(page_objects) != 1:
            print(f"Multiple pages with the same url {page_url} - cannot assign page to issue")
            return
        page_screenshot = PageScreenshot.objects.create(page=page_objects[0], test_results=test_results)
        with tempfile.TemporaryFile() as screenshot_file:
            screenshot_file.write(base64.b64decode(image.encode("ascii")))
            screenshot_file.seek(0)
            page_screenshot.screenshot.save(str(uuid.uuid1()), screenshot_file)

    elif msg_type == "results":
        result = body["result"]

        print(f"Received test results for task {task_id}")

        result_loaded = json.loads(result)

        test_results = task.test_results

        print(f"Writing test_results with id {test_results.id} to task {task.id}")
        task.result = result
        task.last_reported = datetime.datetime.now(datetime.timezone.utc)
        task.log = str(result_loaded["log"])
        print("Saving task")
        task.save()
        print("Task saved!")
        update_test_time_data()

    elif msg_type == "screenshot":
        screenshot_data = body["screenshot_data"]
        screenshot_data_loaded = json.loads(screenshot_data)
        print(
            f"Received screenshot data for test {screenshot_data_loaded['test_name']}, issue {screenshot_data_loaded['uuid']} in task {task_id}"
        )
        if task.test_results is None:
            print("ERROR: Test_results is None, cannot receive screenshots!")
            return
        try:
            target_example = Example.objects.get(
                test_results=task.test_results,
                test__name=screenshot_data_loaded["test_name"],
                uuid=screenshot_data_loaded["uuid"],
            )
        except Example.DoesNotExist:
            print("ERROR: Example does not exist!")
            return
        new_screenshot = ExampleScreenshot.objects.create(example=target_example)
        with tempfile.TemporaryFile() as screenshot_file:
            screenshot_file.write(base64.b64decode(screenshot_data_loaded["screenshot"].encode("ascii")))
            screenshot_file.seek(0)
            new_screenshot.screenshot.save(str(uuid.uuid1()), screenshot_file)
    elif msg_type == "finish":
        test_results = task.test_results

        print(f"Task {task_id} finished")

        api_token.delete_worker_key(key)

        if test_results is None:
            print(f"Cannot finish task {task_id}, test_results is missing!")
            task.status = Task.CRASHED
            task.message = f"Cannot finish task {task_id}, test_results is missing!"
            task.save()
            return

        task.status = Task.SUCCESS
        task.save()
        example_manipulation.group_and_annotate(test_results)
        problems = Issue.objects.filter(test_results=test_results)
        wcag_table_info = xlsdata.cached_wcag_table_info
        vpat_data = xlsdata.cached_vpat_data

        # TODO: optimize by using from web
        product_types = ["Web", "Electronic Docs", "Software", "Authoring Tool", "Closed"]
        for wcag_number in list(wcag_table_info.keys()):
            for product in product_types:
                level = "Select support level"
                remark = ""
                if product == "Web":
                    level = "Supports"
                    remark = vpat_data["wcag"][wcag_number][product]["Supports"]
                conformance_data_vpat = SuccessCriteriaLevel.objects.create(
                    criteria=wcag_number,
                    product_type=product,
                    test_results=test_results,
                    level=level,
                    remark=remark,
                )
        applicable_508 = ["3", "4", "5", "6"]
        applicable_en = ["4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
        fill_508("508", test_results, "3", applicable_508, product_types)
        fill_508("EN", test_results, "4", applicable_en, product_types)

        for wcag_number in list(wcag_table_info.keys()):
            conformance_data = ConformanceLevel.objects.create(
                WCAG=wcag_number, test_results=test_results, level="Supports"
            )
            for problem in problems:
                if wcag_number in problem.wcag:
                    # conformance_data.level = 'Does not support'
                    conformance_data.issues.add(problem)
                    try:
                        conformance_data_vpat = SuccessCriteriaLevel.objects.get(
                            test_results=test_results, criteria=wcag_number, product_type="Web"
                        )
                        conformance_data_vpat.level = "Does Not Support"
                        conformance_data_vpat.remark = vpat_data["wcag"][wcag_number][product]["Does Not Support"]
                        conformance_data_vpat.save()
                    except (Exception, SuccessCriteriaLevel.DoesNotExist) as e:
                        print(e)
            conformance_data.save()
        try:
            update_conformance_level(test_results)
            update_success_criteria_level(test_results)
        except Exception as e:
            print(e)
        update_level_for_section_chapter(test_results, section="508", chapter="3")
        update_level_for_section_chapter(test_results, section="EN", chapter="4")
        regenerate_report(task, None)
    else:
        print(f"Ignoring message type {msg_type}")


@shared_task(queue="rabbitmq_receiver")
def receive_rabbitmq_messages():
    print("Processing rabbitmq messages")
    queue = Queue("testing_interim_results", routing_key="testing_interim_results")
    with Connection(settings.CELERY_BROKER_URL) as connection:
        consumer = connection.Consumer(queue)

        consumer.register_callback(receive_callback)
        try:
            with consumer:
                while True:
                    connection.drain_events(timeout=5)
        except timeout:
            print("No messages for 5 seconds")
            pass


@shared_task(queue="shortlived")
def check_for_planned_tasks():
    print("Looking for planned jobs")
    tasks = PlannedTask.objects.filter(next_start_time__lt=datetime.datetime.now(datetime.timezone.utc))
    if not tasks:
        print("No jobs to run")
    else:
        for task in tasks:
            result = request_test_for_job(task.job)
            if result["task_id"] > 0:
                print(f"{task.job.name} queued")
            else:
                print(f"Didn't queue {task.job.name}")
            if not task.repeatability or task.repeatability == "run_ones":
                task.delete()
                return
            elif task.repeatability == "daily":
                task.next_start_time += datetime.timedelta(days=1)
            elif task.repeatability == "weekly":
                task.next_start_time += datetime.timedelta(weeks=1)
            elif task.repeatability == "yearly":
                """Formula for leap years handling"""
                task.next_start_time = task.start_date + relativedelta(
                    years=task.next_start_time.year - task.start_date.year + 1
                )
            elif task.repeatability == "monthly_date":
                task.next_start_time = task.start_date + relativedelta(
                    months=task.next_start_time.month - task.start_date.month + 1
                )
            elif task.repeatability == "monthly_week_day":
                week_number = (task.start_date.day - 1) // 7 + 1
                new_start_time = task.next_start_time
                n = 0
                while new_start_time.month != task.next_start_time.month + 1:
                    new_start_time = task.next_start_time + relativedelta(
                        months=1, day=1, weekday=task.start_date.weekday(), weeks=week_number - n
                    )
                    if n > 6:
                        raise Exception("Formula error. Out of weeks number")
                    n += 1
                task.next_start_time = new_start_time
            elif task.repeatability == "monthly_last_week_day":
                task.next_start_time += relativedelta(
                    months=2, day=1, days=-1, weekday=WEEKDAYS[task.start_date.weekday()](-1)
                )
            elif task.repeatability == "on_week_days":
                """
                Repeat at custom weekdays, where 0 = monday, ...,  6 = sunday
                and at custom time where time have "str(datetime)||||||" format
                """
                days = list(task.custom_weekdays.split("|"))
                days = [i for i in range(len(days)) if len(days[i]) > 0]
                day_time = list(
                    map(
                        lambda x: datetime.datetime.fromisoformat(x) if x else None,
                        task.custom_weekdays.split("|"),
                    )
                )
                if task.next_start_time.weekday() != days[-1]:
                    task.next_start_time += relativedelta(
                        weekday=days[days.index(task.next_start_time.weekday()) + 1]
                    )
                    run_time = str(day_time[task.next_start_time.weekday()].time()).split(":")
                    task.next_start_time = task.next_start_time.replace(
                        hour=int(run_time[0]), minute=int(run_time[1]), second=int(run_time[2].split(".")[0])
                    )
                else:
                    task.next_start_time += relativedelta(weekday=days[0])
                    run_time = str(day_time[task.next_start_time.weekday()].time()).split(":")
                    task.next_start_time = task.next_start_time.replace(
                        hour=int(run_time[0]), minute=int(run_time[1]), second=int(run_time[2].split(".")[0])
                    )
            else:
                print(f"Failed to start task: Invalid repeatability '{task.repeatability}'!")
            if task.end_date and task.next_start_time <= task.end_date:
                task.delete()
            else:
                task.save()


def create_examples_in_jira(jira_integration_params, task: Task) -> None:
    examples = Example.objects.none()
    issues_WCAG = Issue.objects.filter(test_results=task.test_results, is_best_practice=False)
    for issue in issues_WCAG:
        examples |= Example.objects.filter(issue=issue, severity="FAIL")
    if hasattr(task, "jira_worker_task"):
        task.jira_worker_task.delete()
    jira_worker_task = JiraWorkerTask.objects.create(total_examples=len(examples), task=task)
    example_ids = [example.id for example in examples]
    _do_create_examples_in_jira.delay(jira_worker_task.id, jira_integration_params.id, example_ids)


@shared_task(queue="shortlived")
def _do_create_examples_in_jira(jira_worker_task_id, jira_integration_params_id, example_ids) -> None:
    print("Starting JIRA upload")
    jira_worker_task = JiraWorkerTask.objects.get(id=jira_worker_task_id)
    jira_worker_task.status = JiraWorkerTask.RUNNING
    jira_worker_task.save()

    examples = [Example.objects.get(id=example_id) for example_id in example_ids]
    jira_integration_params = JiraIntegrationParams.objects.get(id=jira_integration_params_id)
    try:
        jira_integration = JiraIntegration(jira_integration_params)
        jira_integration.create_examples_in_jira(examples)
        jira_worker_task.status = JiraWorkerTask.SUCCESS
        jira_worker_task.total_issues = jira_integration.created_issues
        jira_worker_task.reopened_issues = jira_integration.reopened_issues
        jira_worker_task.processed_examples = jira_integration.processed_examples
        jira_worker_task.duplicated_issues = jira_integration.duplicated_issues
        print("JIRA upload finished")
    except Exception as e:
        jira_worker_task.status = JiraWorkerTask.FAILED
        print("JIRA upload failed")
        print(e)
    jira_worker_task.save()
