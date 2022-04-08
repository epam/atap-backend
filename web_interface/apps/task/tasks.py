import datetime
import logging
import queue
import traceback
from itertools import chain
from json import loads
from os import environ
from re import sub
from threading import Thread
from time import time
from typing import Optional, Collection, Union

import requests
from celery import shared_task
from celery.result import AsyncResult
from django.conf import settings
from django.core.cache import cache
from django.db.models import Subquery
from kombu import Connection, Exchange
from lxml import html
from requests.adapters import HTTPAdapter, Retry
from selenium import webdriver

from framework import activity
from framework.tools.sitemap import SiteMap
from web_interface.apps.issue.models import Example
from web_interface.apps.jira.models import JiraWorkerTask, JiraIntegrationParams
from web_interface.apps.page.models import Page
from web_interface.apps.project.models import Project
from web_interface.apps.report import report_generator
from web_interface.apps.report.models import Issue
from web_interface.apps.task.models import Task, SitemapTask, Report
from web_interface.apps.task.task_functional.callback_progress import (
    receive_rabbitmq_messages_func,
    check_for_planned_tasks_func,
)
from web_interface.apps.task.task_functional.estimate_time import update_page_size_func, update_job_test_time_func
from web_interface.apps.task.task_functional.test_page import init_root_logger, TestPageStatusCapsule
from web_interface.backend.jira.JiraIntegration import JiraIntegration
from web_interface.celery import control

SITEMAP_QUOTA = 2

root_logger, console_out = init_root_logger()
formatter = logging.Formatter("[%(asctime)s] (%(threadName)s) %(name)s/%(levelname)s:%(message)s")
console_out.setFormatter(formatter)

if "USE_DOCKER" in environ:
    HOST_URL = "http://nginx:80"
else:
    HOST_URL = "http://localhost:8000"


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


def generate_sitemap(project_id, depth_level: Optional[int] = None) -> bool:
    if is_sitemap_running(project_id) or get_remaining_sitemap_quota() <= 0:
        return False
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
    result = _process_sitemap.delay(project_id, depth_level)
    SitemapTask.objects.create(project_id=project_id, celery_task_id=result.task_id, status=SitemapTask.RUNNING)

    return True


def get_remaining_sitemap_quota() -> int:
    return SITEMAP_QUOTA - SitemapTask.objects.filter(status=SitemapTask.RUNNING).count()


def is_activity_running(activity_id) -> dict:
    result = AsyncResult(activity_id)
    if result.ready():
        return {"running": False, "status": result.state, "result": result.result}
    return {"running": True, "status": result.state, "result": result.result}


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
        "page_resolution": None,
    }

    try:
        driver = webdriver.Firefox()
        activities = activity.load_activities(page_info, driver)
        activities[0].get(driver)
    except Exception as e:
        return False, f"Failed to open activity: {e}"

    return True, "Activity validated"


def _verify_sitemap_tasks(selected_project_id):
    if cache.get("sitemap_task_verified") is not None:
        return False
    cache.set("sitemap_task_verified", time(), 60)

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


def _delete_old_report(report: Report) -> None:
    old_reports = Report.objects.filter(task=report.task)
    old_reports = old_reports.exclude(pk=report.id)
    old_reports.delete()


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


def _task_fail(self, exc, task_id, args, kwargs, einfo) -> None:
    worker_key = kwargs.get("worker_key")

    # ? task_id is reassigned
    task_id = kwargs.get("task_id")
    # ! Not Found: /worker/fail_task
    requests.post(HOST_URL + "/worker/fail_task", data={"worker_key": worker_key, "task_id": task_id})


@shared_task(queue="shortlived")
def check_for_planned_tasks():
    check_for_planned_tasks_func()


@shared_task(queue="shortlived")
def check_if_task_alive(task_id):
    task = Task.objects.get(id=task_id)
    print(f"Watching task {task.celery_task_id}")
    if task.status in [Task.RUNNING, Task.QUEUED]:
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


@shared_task(queue="shortlived")
def generate_report(report_id):
    report = Report.objects.get(id=report_id)
    report.status = Report.GENERATING
    report.save()

    task = report.task
    name = task.target_job.project.name + " " + task.target_job.name
    filename = f"{name}_{task.date_started}.docx"
    filename = sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)
    print(f"Generating report {filename}...")
    report.generated_report.save(filename, report_generator.generate_report(task, report.delta_starting_task))
    report.status = Report.SUCCESS
    report.save()

    _delete_old_report(report)

    print("Report generated!")


@shared_task(queue="rabbitmq_receiver")
def receive_rabbitmq_messages():
    receive_rabbitmq_messages_func()


@shared_task(bind=True, on_failure=_task_fail, queue="longlived")
def test_page(self, project_info: dict, task_id: int, worker_key: str):
    TestPageStatusCapsule(self, project_info, task_id, worker_key).test_page_func()


# tmp disabled
@shared_task(queue="shortlived")
def update_page_size(page_id):
    return update_page_size_func(page_id)


@shared_task(queue="shortlived")
def update_job_test_time(job_id):
    update_job_test_time_func(job_id)


@shared_task(queue="shortlived")
def verify_tasks_running():
    # deleted code
    return


@shared_task(queue="shortlived")
def _do_create_examples_in_jira(jira_worker_task_id, jira_integration_params_id, example_ids) -> None:
    print("Starting JIRA upload")
    jira_worker_task = JiraWorkerTask.objects.get(id=jira_worker_task_id)
    jira_worker_task.status = JiraWorkerTask.RUNNING
    jira_worker_task.save()

    examples = list(Example.objects.filter(id__in=example_ids))
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


@shared_task(queue="shortlived_realtime")
def _process_sitemap(project_id, depth_level: Optional[int] = None):
    project = Project.objects.get(id=project_id)

    if loads(project.options)["auth_required"]:
        mode = "auth"
    else:
        mode = "simple"

    sitemap = SiteMap(project.url, mode, options=project.options, depth_level=depth_level)
    sitemap.get_sitemap()
    local_pages = []

    def retrieve_page_titles(sitemap, number_of_workers: int) -> None:
        class Worker(Thread):
            def __init__(self, request_queue: queue.Queue):
                Thread.__init__(self)
                self.queue = request_queue

            def run(self) -> None:

                while True:
                    content = self.queue.get()
                    if content == "":
                        break
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0",
                    }
                    try:
                        response = requests.get(content["url"], headers=headers)
                        response.encoding = "utf-8"
                        if response.status_code == 502:
                            response = _requests_retry_session(retries=2).get(content["url"], headers=headers)
                        parsed_body = html.fromstring(response.text)
                        title = parsed_body.xpath("//title/text()")[0]
                        if "404" in title:
                            continue
                    except:
                        print(traceback.format_exc())
                        title = content["url"]
                    local_page = Page(name=title, url=content["url"], project=project)
                    local_page.parent_url = content["parent"]
                    local_pages.append(local_page)
                    self.queue.task_done()

        queue_ = queue.Queue()
        for item in sitemap:
            queue_.put(item)

        # Workers keep working till they receive an empty string
        for _ in range(number_of_workers):
            queue_.put("")

        workers = []
        for _ in range(number_of_workers):
            worker = Worker(queue_)
            worker.start()
            workers.append(worker)

        # Join workers to wait till they finished
        for worker in workers:
            worker.join()

    retrieve_page_titles(sitemap.sitemap, 16)

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


def _requests_retry_session(
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


@shared_task(queue="shortlived")
def kill_task(celery_task_id) -> None:
    print(f"Force killing task {celery_task_id}")
    control.revoke(celery_task_id, terminate=True, signal="SIGKILL")
