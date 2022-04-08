import base64
import datetime
import uuid
from tempfile import TemporaryFile
from socket import timeout
from json import loads
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from kombu import Queue, Connection
from framework import xlsdata
from web_interface.apps.issue import example_manipulation
from web_interface.apps.issue.models import PageScreenshot, Example, ExampleScreenshot
from web_interface.apps.report.models import Issue, SuccessCriteriaLevel, ConformanceLevel
from web_interface.apps.framework_data.models import TestTiming, Test, TestResults
from web_interface.apps.task_planner.models import PlannedTask
from web_interface.backend.conformance import (
    fill_508,
    update_conformance_level,
    update_success_criteria_level,
    update_level_for_section_chapter,
)
from django.conf import settings
from web_interface.apps.activity.models import Activity
from web_interface.apps.page.models import Page
from web_interface.apps.task.models import Task
from web_interface.apps.task import api_token
from web_interface.apps.task import tasks


WEEKDAYS = {0: MO, 1: TU, 2: WE, 3: TH, 4: FR, 5: SA, 6: SU}


def cancel_if_callback_occurred(func):
    def wrapper(callback_instance):
        if not callback_instance.new_progress_callback:
            func(callback_instance)

    return wrapper


def check_for_planned_tasks_func():
    tasks = PlannedTask.objects.filter(next_start_time__lt=datetime.datetime.now(datetime.timezone.utc))

    if not tasks:
        print("No jobs to run")
    else:
        _schedule_possible_repeatable_tasks(tasks)


def receive_rabbitmq_messages_func():
    print("Processing rabbitmq messages")
    queue = Queue("testing_interim_results", routing_key="testing_interim_results")
    with Connection(settings.CELERY_BROKER_URL) as connection:
        consumer = connection.Consumer(queue)

        consumer.register_callback(ReceiveCallbackTaskCapsule().receive_callback)
        try:
            with consumer:
                while True:
                    connection.drain_events(timeout=5)
        except timeout:
            print("No messages for 5 seconds")


def request_test_for_job(job):
    print("Requesting test for " + str(job.id))

    if Task.objects.filter(target_job=job, status__in=(Task.QUEUED, Task.RUNNING)).exists():
        print(f"Task for {job.id} already running")
        return {"task_id": -1, "status": "already_running", "celery_task_id": ""}

    test_list, pages, project, options = _set_testing_variables(job)
    screen_resolutions = job.resolutions.split(",")
    page_infos = _build_page_infos(pages, options, screen_resolutions)

    task = Task.objects.create(
        date_started=datetime.datetime.now(datetime.timezone.utc), target_job=job, status=Task.QUEUED, message=""
    )
    _set_job_last_test(job, task)

    result = _get_page_test_result(task, test_list, page_infos, project)
    # check_if_task_alive.apply_async((task.id,), countdown=60)
    task.celery_task_id = result.id
    task.save()

    return {"task_id": task.id, "status": "ok", "celery_task_id": result.id}


class ReceiveCallbackTaskCapsule:
    def receive_callback(self, body, message):
        # TODO try decorator
        self.new_progress_callback = False

        self.body = body
        self.__set_callback_providers()
        self.task.save()
        message.ack()

        if not api_token.check_worker_key(self.key, self.task):
            print("Request denied, invalid token!")
            return

        self.__update_interim_progress()
        self.__update_set_running()
        self.__update_fail_task()
        self.__update_interim_test_result()
        self.__update_page_screenshot()
        self.__update_results()
        self.__update_screenshot()
        self.__update_finish()

        if not self.new_progress_callback:
            print(f"Ignoring message type {self.msg_type}")

    def __set_callback_providers(self):
        self.task_id = self.body["task_id"]
        self.task = Task.objects.get(id=self.task_id)
        self.task.last_reported = datetime.datetime.now(datetime.timezone.utc)
        self.msg_type = self.body["type"]
        self.key = self.body["worker_key"]

    @cancel_if_callback_occurred
    def __update_interim_progress(self):
        if self.msg_type == "interim":
            self.new_progress_callback = True

            self.task.progress = self.body["progress"]
            self.task.save()

    @cancel_if_callback_occurred
    def __update_set_running(self):
        if self.msg_type != "set_running":
            return

        self.new_progress_callback = True

        print(f"Setting task {self.task_id} status to RUNNING")
        task_status_before = self.task.status

        test_results = TestResults.objects.create()
        self.task.test_results = test_results
        self.task.save()

        if task_status_before != Task.ABORTED:
            self.task.status = Task.RUNNING
            self.task.last_reported = datetime.datetime.now(datetime.timezone.utc)
            self.task.celery_task_id = self.body["celery_task_id"]
            self.task.save()

    @cancel_if_callback_occurred
    def __update_fail_task(self):
        if self.msg_type == "fail_task":
            self.new_progress_callback = True

            print(f"Task {self.task_id} failed")
            if "message" in self.body:
                self.task.message = self.body["message"]
            self.task.status = Task.CRASHED
            self.task.log = str(self.body["log"]) if "log" in self.body else "No log received from worker"
            self.task.save()

            api_token.delete_worker_key(self.key)

    @cancel_if_callback_occurred
    def __update_interim_test_result(self):
        if self.msg_type != "interim_test_result":
            return

        self.new_progress_callback = True

        test = self.body["test"]
        print(f"Received interim test results for task {self.task_id}, test {test['name']}")
        test_results = self.task.test_results
        test_obj = Test.objects.create(
            name=test["name"],
            status=test["status"],
            support_status=test["support_status"],
            checked_elements=test["checked_elements"],
            test_results=test_results,
            problematic_pages=test["problematic_pages"],
        )

        # TODO enable
        # ! temp disable
        # for run_time in test["run_times"]:
        #     print("RUN_TIME", run_time)
        #     page_params = Page.objects.filter(url=run_time[0]).latest("id").page_size_data
        #     TestTiming.objects.create(name=test["name"], run_times=run_time[2], page_size_data=page_params)

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
                important_example=issue["important_example"],
                force_best_practice=issue["force_best_practice"],
                affected_resolutions=issue["page_resolution"],
            )
            print(f"Created issue with uuid {issue['uuid']}")
            issue_obj.pages.clear()

            for page in issue["pages"]:
                page_objects = Page.objects.filter(project=self.task.target_job.project, url=page)
                if len(page_objects) != 1:
                    print(f"Multiple pages with the same url {page} - cannot assign page to issue")
                    break
                # print(f"Adding page {page_obj.id} {page_obj.url}")
                issue_obj.pages.add(page_objects[0])
                print(f"Added page {page_objects[0].name}")
            issue_obj.save()

        example_manipulation.group_and_annotate(test_results)

    @cancel_if_callback_occurred
    def __update_page_screenshot(self):
        if self.msg_type == "page_screenshot":
            self.new_progress_callback = True

            test_results = self.task.test_results
            page_url = self.body["url"]
            image = self.body["image"]

            print(f"Received page screenshot for {page_url}")
            page_objects = Page.objects.filter(project=self.task.target_job.project, url=page_url)

            if len(page_objects) != 1:
                print(f"Multiple pages with the same url {page_url} - cannot assign page to issue")
                return
            page_screenshot = PageScreenshot.objects.create(page=page_objects[0], test_results=test_results)

            with TemporaryFile() as screenshot_file:
                screenshot_file.write(base64.b64decode(image.encode("ascii")))
                screenshot_file.seek(0)
                page_screenshot.screenshot.save(str(uuid.uuid1()), screenshot_file)

    @cancel_if_callback_occurred
    def __update_results(self):
        # * triggers after uploading tests results (so after screenshooting)
        if self.msg_type == "results":
            self.new_progress_callback = True

            result = self.body["result"]
            print(f"Received test results for task {self.task_id}", result)

            result_loaded = loads(result)

            print(f"Writing test_results with id {self.task.test_results.id} to task {self.task.id}")
            self.task.result = result
            self.task.last_reported = datetime.datetime.now(datetime.timezone.utc)
            self.task.log = str(result_loaded["log"])

            print("Saving task")
            self.task.save()
            print("Task saved!")

    @cancel_if_callback_occurred
    def __update_screenshot(self):
        if self.msg_type == "screenshot":
            self.new_progress_callback = True

            screenshot_data_loaded = loads(self.body["screenshot_data"])
            print(
                f"Received screenshot data for test {screenshot_data_loaded['test_name']}, issue {screenshot_data_loaded['uuid']} in task {self.task_id}"
            )

            if self.task.test_results is None:
                print("ERROR: Test_results is None, cannot receive screenshots!")
                return

            try:
                target_example = Example.objects.get(
                    test_results=self.task.test_results,
                    test__name=screenshot_data_loaded["test_name"],
                    uuid=screenshot_data_loaded["uuid"],
                )
            except Example.DoesNotExist:
                print("ERROR: Example does not exist!")
                return

            new_screenshot = ExampleScreenshot.objects.create(example=target_example)
            with TemporaryFile() as screenshot_file:
                screenshot_file.write(base64.b64decode(screenshot_data_loaded["screenshot"].encode("ascii")))
                screenshot_file.seek(0)
                new_screenshot.screenshot.save(str(uuid.uuid1()), screenshot_file)

    @cancel_if_callback_occurred
    def __update_finish(self):
        if self.msg_type != "finish":
            return

        self.new_progress_callback = True

        test_results = self.task.test_results
        print(f"Task {self.task_id} finished")
        api_token.delete_worker_key(self.key)

        if test_results is None:
            print(f"Cannot finish task {self.task_id}, test_results is missing!")
            self.task.status = Task.CRASHED
            self.task.message = f"Cannot finish task {self.task_id}, test_results is missing!"
            self.task.save()
            return

        self.task.status = Task.SUCCESS
        self.task.save()
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
        tasks.regenerate_report(self.task, None)


def _check_task_queued(task, info):
    if info["task_id"] > 0:
        print(f"{task.job.name} queued")
    else:
        print(f"Didn't queue {task.job.name}")


def _init_partial_repeat_periods(task):
    return dict(
        daily={"days": 1},
        weekly={"weeks": 1},
        yearly={"years": task.next_start_time.year - task.start_date.year + 1},
        monthly_date={"months": task.next_start_time.month - task.start_date.month + 1},
        monthly_last_week_day={
            "months": 2,
            "day": 1,
            "days": -1,
            "weekday": WEEKDAYS[task.start_date.weekday()](-1),
        },
    )


def _check_next_time_validity_and_save(task):
    if task.end_date and task.next_start_time <= task.end_date:
        task.delete()
    else:
        task.save()


def _updated_task_time_monthly_week_day(task):
    week_number = (task.start_date.day - 1) // 7 + 1
    new_start_time = task.next_start_time
    n = 0

    while new_start_time.month != task.next_start_time.month + 1:
        new_start_time = task.next_start_time + relativedelta(
            months=1, day=1, weekday=task.start_date.weekday(), weeks=week_number - n
        )
        if n > 6:
            raise NameError("Formula error. Out of weeks number")
        n += 1

    return new_start_time


def _updated_task_time_on_week_days(task):
    days = list(task.custom_weekdays.split("|"))
    days = [i for i in range(len(days)) if len(days[i]) > 0]
    day_time = list(
        map(
            lambda x: datetime.datetime.fromisoformat(x) if x else None,
            task.custom_weekdays.split("|"),
        )
    )

    if task.next_start_time.weekday() != days[-1]:
        task.next_start_time += relativedelta(weekday=days[days.index(task.next_start_time.weekday()) + 1])
    else:
        task.next_start_time += relativedelta(weekday=days[0])

    run_time = str(day_time[task.next_start_time.weekday()].time()).split(":")

    return task.next_start_time.replace(
        hour=int(run_time[0]), minute=int(run_time[1]), second=int(run_time[2].split(".")[0])
    )


def _schedule_possible_repeatable_tasks(tasks):
    for task in tasks:
        result = request_test_for_job(
            task.job
        )  # expect task.job AttributeError: 'Task' object has no attribute 'job', maybe target_job

        _check_task_queued(task, result)

        if not task.repeatability or task.repeatability == "run_ones":
            task.delete()
            return

        period_map = _init_partial_repeat_periods(task)
        if task.repeatability in ["daily", "weekly"]:
            task.next_start_time += datetime.timedelta(**period_map[task.repeatability])
        elif task.repeatability in ["monthly_date", "yearly", "monthly_last_week_day"]:
            """Formula for leap handling"""
            if task.repeatability != "monthly_last_week_day":
                task.next_start_time = task.start_date
            task.next_start_time += relativedelta(**period_map[task.repeatability])
        elif task.repeatability == "monthly_week_day":
            task.next_start_time = _updated_task_time_monthly_week_day(task)
        elif task.repeatability == "on_week_days":
            """
            Repeat at custom weekdays, where 0 = monday, ...,  6 = sunday
            and at custom time where time have "str(datetime)||||||" format
            """
            task.next_start_time = _updated_task_time_on_week_days(task)
        else:
            print(f"Failed to start task: Invalid repeatability '{task.repeatability}'!")

        _check_next_time_validity_and_save(task)


def _set_testing_variables(job):
    return job.test_list.split(","), job.pages.select_related("project"), job.project, job.project.options


def _get_activity_data_of_page(page):
    return [
        {
            "name": activity.name,
            "side_file": activity.side_file.read().decode("utf-8") if activity.side_file else "",
            "element_click_order": activity.click_sequence.split(";")
            if activity.click_sequence is not None
            else None,
        }
        for activity in Activity.objects.filter(page=page)
    ]


def _init_page_info(page, activity_infos, options, resolution=None):
    info_obj = {
        "url": page.url,
        "options": options,
        "name": page.name,
        "page_after_login": page.project.page_after_login,
        "page_resolution": resolution,
    }

    if len(activity_infos):
        info_obj["activities"] = activity_infos

    return info_obj


def _init_project_info(project, page_infos, test_list, vpat_reports, audit_reports):
    return {
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


def _set_job_last_test(job, task):
    job.last_test = task.date_started
    job.save()
    job.project.last_test = task.date_started
    job.project.save()


def _build_page_infos(pages, options, screen_resolutions):
    info_list = []

    for page in pages:
        if not screen_resolutions:
            activity_infos = _get_activity_data_of_page(page)
            page_info = _init_page_info(page, activity_infos, options)
            info_list.append(page_info)
        else:
            for resolution in screen_resolutions:
                activity_infos = _get_activity_data_of_page(page)
                page_info = _init_page_info(page, activity_infos, options, resolution)
                info_list.append(page_info)
    return info_list


def _get_page_test_result(task, test_list, page_infos, project):
    project_info = _init_project_info(project, page_infos, test_list, "", "")
    token = api_token.create_worker_key(task)

    return tasks.test_page.delay(project_info=project_info, task_id=task.id, worker_key=token)
