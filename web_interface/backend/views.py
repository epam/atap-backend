import json
import re
import tempfile

import os
import requests
from django.http import (
    HttpResponse, HttpResponseBadRequest, FileResponse, HttpResponseRedirect, HttpResponseServerError
)
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

from framework.libs.basic_groups import HARDCODE_TESTS_BASIC_1, HARDCODE_TESTS_BASIC_2, BASED_TEST_HARDCODE
from framework.report import vpat_docx_report
from web_interface.apps.framework_data.models import AvailableTest
from django.db.models import Q
from web_interface.apps.job.models import Job
from web_interface.apps.project.models import Project
from web_interface.apps.report import report_generator
from web_interface.apps.report.models import VpatReportParams
from web_interface.apps.report.models import Report
from web_interface.apps.task import api_token
from web_interface.apps.task.models import Task
from web_interface.apps.task.tasks import (
    is_sitemap_running, abort_task, request_test_for_job, is_activity_running, verify_tasks_running
)
from web_interface.apps.jira.models import JiraIntegrationParams
from web_interface.backend import url_checker



def download_report(request):
    if "vpat_report_id" in request.GET:
        task = Task.objects.get(id=request.GET["vpat_task_id"])
        report_params = VpatReportParams.objects.get(id=request.GET["vpat_report_id"])
        name = task.target_job.project.name + ' ' + report_params.name
        extension = ".docx"
        report_file = tempfile.NamedTemporaryFile()
        vpat_docx_report.VpatReport(
            task=task,
            report_params=report_params,
        ).create(report_file.name)

        report_file.seek(0)
        filename = f"{name}_{task.date_started}{extension}"
        filename = re.sub(r"""[^a-zA-Z0-9_\-\.]""", "_", filename)
        response = FileResponse(report_file, filename=filename)
        response['Content-Disposition'] = f'filename={filename}'
        return response

    if "report_id" in request.GET:
        report = Report.objects.get(id=request.GET["report_id"])
        name = report.task.target_job.project.name + ' ' + report.task.target_job.name
        if report.name.endswith("(PDF)"):
            extension = ".pdf"
        else:
            extension = ".docx"

        filename = f"{name}_{report.task.date_started}{extension}"
        filename = re.sub(r"""[^a-zA-Z0-9_\-\.]""", "_", filename)
        response = FileResponse(report.file, filename=filename)
        response['Content-Disposition'] = f'filename={filename}'
    else:
        wcag = '21'
        if 'wcag' in request.GET:
            wcag = request.GET["wcag"]
        task = Task.objects.get(id=request.GET["task_id"])
        name = task.target_job.project.name + ' ' + task.target_job.name
        extension = ".docx"
        report_file = report_generator.generate_report(task, request.user, wcag)
        filename = f"{name}_{task.date_started}{extension}"
        filename = re.sub(r"""[^a-zA-Z0-9_\-\.]""", "_", filename)
        response = FileResponse(report_file, filename=filename)
        response['Content-Disposition'] = f'filename={filename}'
    return response


@cache_page(1800)
def get_available_tests(request):
    tests_list = []
    current_env = os.environ.get("CURRENT_ENV", "DEV")
    print(current_env)
    #temporary hot fix 
    if current_env in ("PROD", "PROD_DEBUG"):
        queryset = AvailableTest.objects.filter(Q(name__in=BASED_TEST_HARDCODE) | ~Q(name__contains='test')).order_by("human_name")
    else:
        queryset = AvailableTest.objects.order_by("human_name")
    for test in queryset:
        tests_list.append({
            "name": test.name,
            "human_name": test.human_name
        })
    is_demo_user = request.user.groups.filter(name='demo').exists()
    with open(r"framework/time_of_tests/average_time.json", "r", encoding="utf-8") as f:
        time_data = json.load(f)
    for test in tests_list:
        if test["name"] in BASED_TEST_HARDCODE:
            test['base'] = True
        elif not test["name"].startswith("test_"):
            test["axe"] = True
        try:
            test["average_time"] = time_data[test["name"]]
        except KeyError:
            test["average_time"] = False
        if test["name"] in HARDCODE_TESTS_BASIC_1:
            test['basic_1'] = True
        if test["name"] in HARDCODE_TESTS_BASIC_2:
            test['basic_2'] = True
    return HttpResponse(json.dumps(tests_list))


def get_status(request):
    verify_tasks_running()

    projects = Project.objects.filter(users=request.user)
    if request.user.groups.filter(name='Admin').exists():
        running_tasks = Task.objects.filter(status=Task.RUNNING).order_by('-date_started')
    else:
        running_tasks = Task.objects.filter(status=Task.RUNNING, target_job__project__in=projects).order_by("-date_started")

    data = {
        "running_tasks": list()
    }

    for running_task in running_tasks:
        progress_json = running_task.progress
        if progress_json is None:
            cur_progress = {
                "overall_progress": "Starting...",
                "thread_count": 0,
                "thread_status": {},
                "tasks_complete": 0,
                "tasks_count": 1
            }
        else:
            try:
                cur_progress = json.loads(progress_json)
            except json.JSONDecodeError:
                print(f"Failed to decode '{progress_json}'")
                cur_progress = {
                    "overall_progress": "ERROR: Cannot decode task progress!",
                    "thread_count": 0,
                    "thread_status": {},
                    "tasks_complete": 0,
                    "tasks_count": 1
                }

        task_data = {
            "cur_task": running_task.id,
            "cur_page_name": 'Job: <a href="/jobs/?project_id=' + str(
                running_task.target_job.project.id) + '">' + running_task.target_job.name + '</a>, Project: <a href="/project/?project=' + str(
                running_task.target_job.project.id) + '">' + running_task.target_job.project.name + '  </a>',
            "cur_progress": cur_progress
        }

        data["running_tasks"].append(task_data)

    if "project_id" in request.GET:
        data["is_sitemap_running"] = is_sitemap_running(request.GET['project_id'])

    all_queued_count = Task.objects.filter(status=Task.QUEUED).count()
    if request.user.groups.filter(name='Admin').exists():
        queued_tasks = Task.objects.filter(status=Task.QUEUED).order_by('date_started')
    else:
        queued_tasks = Task.objects.filter(
            status=Task.QUEUED, target_job__project__in=projects
        ).order_by('date_started')

    queue_data = list()
    for queued_task in queued_tasks:
        queue_data.append(
            {
                "id": queued_task.id,
                "project": queued_task.target_job.project.name,
                "project_id": queued_task.target_job.project.id,
                "job": queued_task.target_job.name,
                "page": None,
                "date_started": str(queued_task.date_started)
            }
        )
    data["queue_data"] = queue_data
    data["all_queued_count"] = all_queued_count
    return HttpResponse(json.dumps(data))


def cancel_task(request):
    try:
        task_id = request.POST["task_id"]
        print(task_id)
        task = Task.objects.get(id=task_id)
        abort_task(task)
        return HttpResponseRedirect("/test_progress/")
    except (Task.DoesNotExist, ValueError):
        return HttpResponse("INVALID_TASK")


@csrf_exempt
def get_task_status(request):
    if "task_id" not in request.POST:
        return HttpResponseBadRequest(json.dumps({
            "status": "ERROR",
            "message": "task_id not provided"
        }))
    try:
        task = Task.objects.get(celery_task_id=request.POST["task_id"])
        if task.status != Task.SUCCESS:
            return HttpResponse(json.dumps({
                "status": "ok",
                "task_status": task.status,
                "task_progress": json.loads(task.progress)
            }))
        else:
            return HttpResponse(json.dumps({
                "status": "ok",
                "task_status": task.status,
                "result": json.loads(task.result),
            }))
    except Task.DoesNotExist:
        return HttpResponse(json.dumps({
            "status": "ok",
            "task_status": "DOESNOTEXIST"
        }))


@csrf_exempt
def start_task(request):
    if "job_id" not in request.POST:
        return HttpResponseBadRequest(json.dumps({
            "status": "ERROR",
            "message": f"Bad request: job_id not provided"
        }))

    try:
        job = Job.objects.get(id=request.POST["job_id"])
        pages = job.pages.all()
        project = job.project
    except Job.DoesNotExist:
        return HttpResponseBadRequest(json.dumps({
            "status": "ERROR",
            "message": f"Bad request: job with id {request.POST['job_id']} not found"
        }))
    # for page in pages:
    #     url = page.url
    #     if not check_url(url):
    #         return HttpResponseBadRequest(json.dumps({
    #             "status": "ERROR",
    #             "message": f"Bad request: testable site is not reachable"
    #         }))
    request_test_for_job(job)
    return HttpResponse(json.dumps({
        "status": "ok"
    }))


def create_token(request):
    if request.method == "POST":
        try:
            projects = Project.objects.filter(users=request.user)
            project = projects.get(id=request.POST["project_id"])
            token = api_token.create_token(request.user, project)
            return HttpResponse(json.dumps({
                "status": "ok",
                "token": token
            }))
        except Project.DoesNotExist:
            return HttpResponse(json.dumps({"status": "Project does not exist"}))


def revoke_token(request):
    if request.method == "POST":
        api_token.delete_token(request.POST["token_id"], request.user)
        return HttpResponseRedirect("/api_keys/")


def url_validation(request):
    url = request.POST['url']
    response = requests.head(url)
    if response.status_code == 200:
        return HttpResponse(json.dumps({'success': True}))
    else:
        check_url_response = url_checker.check_url(url)
        if check_url_response.is_valid:
            return HttpResponse(json.dumps({'success': True}))
        else:
            HttpResponseServerError()
    return HttpResponseServerError()


def activity_validation(request):
    element_locators = list(filter(lambda x: x, request.POST["click_sequence"].split(';')))
    commands = []
    if element_locators:
        for element_locator in element_locators:
            commands.append({"command": "click",
                             "target": f"css={element_locator}",
                             "targets": [],
                             "value": ""})

    elif request.POST["side_file"]:
        commands = eval(str(request.POST["side_file"]).replace('true', 'True').
                        replace('false', 'False'))['tests'][0]['commands']

    project = Project.objects.filter(id=request.POST['project']).first()
    activity_info = {
        'project': request.POST['project'],
        'name': f"Check validation activity",
        "url": request.POST['url'],
        "options": project.options if eval(project.options.replace('false', 'False').replace('true', 'True'))[
            'auth_required'] else '',
        'page_after_login': request.POST['page_after_login'] == 'true',
        'commands': commands
    }

    return HttpResponse(json.dumps({'success': True, 'activity_id': 0}))


def activity_running(request):
    info = is_activity_running(request.GET['activity_id'])
    return HttpResponse(json.dumps({'success': True,
                                    'is_running': info['running'],
                                    'status': info['status'],
                                    'result': str(info['result'])}))

