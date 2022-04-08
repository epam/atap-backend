import csv
from typing import Optional, Tuple

from django.http import HttpResponse
from django.db.models import Subquery, OuterRef
from rest_framework.response import Response
from rest_framework import status

from web_interface.apps.job.models import Job
from web_interface.apps.task.models import Task
from web_interface.apps.task import tasks
from web_interface.apps.task.task_functional import estimate_time
from web_interface.apps.report.models import ConformanceLevel, Issue, SuccessCriteriaLevel


def jobs_sorted_ran_last_query() -> Subquery:
    return (
        Job.objects.select_related("project")
        .prefetch_related("task_set", "vpatreportparams_set", "pages")
        .annotate(
            last_task_status=_last_task_status_query(),
            last_task_started=_last_task_started_query(),
        )
        .order_by("last_task_started")
    )


def abort_job_tasks(tasks_query) -> None:
    for task in tasks_query:
        tasks.abort_task(task)


def download_timings_db(test_timings_queryset) -> HttpResponse:
    # * delete page_size_data of False
    test_timings_queryset.model.objects.filter(
        name__isnull=True, page_size_data__isnull=True, run_times__isnull=True
    ).delete()

    opts = test_timings_queryset.model._meta
    response = HttpResponse(content_type="text/csv")
    # * force download
    response["Content-Disposition"] = "attachment; filename=test_data.csv"

    writer = csv.writer(response)
    field_names = [field.name for field in opts.fields]
    # * headers
    writer.writerow(field_names)
    # * data
    for obj in test_timings_queryset:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response


def get_calculated_job_time(request_serializer) -> int:
    data = request_serializer.validated_data

    return estimate_time.calculated_job_runtime(data["pages"], data["tests"])


def get_estimated_job_time(request_serializer) -> int:
    data = request_serializer.validated_data

    return estimate_time.estimated_job_execution_time(data["pages"], data["tests"])


def running_jobs_query(start_request) -> Subquery:
    return (
        Job.objects.filter(project__users=start_request.user, task__status__in=(Task.QUEUED, Task.RUNNING))
        .distinct()
        .count()
    )


def created_jobs_number_query(clone_request) -> Subquery:
    return Job.objects.filter(project__users=clone_request.user).count()


def demo_subscription_ended_response(task_request, jobs_query_fn) -> Optional[Response]:
    if jobs_query_fn.__name__ == "running_jobs_query":
        running_jobs_count = running_jobs_query(task_request)

        if running_jobs_count >= task_request.user.demo_permissions.running_jobs_quota:
            return _demo_user_bad_request_response(
                message="The quota for execution jobs has been exceeded. "
                "Contact your administrator to change your subscription plan."
            )
    elif jobs_query_fn.__name__ == "created_jobs_number_query":
        jobs_created_count = Job.objects.filter(project__users=task_request.user).count()

        if jobs_created_count >= task_request.user.demo_permissions.jobs_quota:
            return _demo_user_bad_request_response(
                message="The quota for execution jobs has been exceeded. "
                "Contact your administrator to change your subscription plan."
            )

    raise NameError("Subscription Quota Exceeded")


def task_queued_response(task_id) -> Optional[Response]:
    if task_id == -1:
        return Response(
            data={"non_field_errors": ["Task already in queue for this job"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    raise NameError("Adding task to queue")


def create_job_clone(job) -> Job:
    job_clone = Job.objects.get(pk=job.pk)
    job_clone.pk, job_clone.name = (
        None,
        f"{job_clone.name} (Copy)",
    )
    job_clone.save()

    return job_clone


def transfer_job_parameters(test_results, cloned_test_results, wcag_levels) -> None:
    _save_issue_parameters(test_results, cloned_test_results, wcag_levels)
    _save_success_criteria_levels(test_results)


def copy_cloned_job_groups(job, test_results, conformance_levels) -> None:
    try:
        old_test_results = Task.objects.filter(target_job=job).latest().test_results
    except AttributeError:
        pass
    else:
        transfer_job_parameters(old_test_results, test_results, conformance_levels)


def save_latest_task(latest_task_job, cloned_job) -> Tuple[Subquery, Subquery]:
    latest_task = Task.objects.filter(target_job=latest_task_job).latest()
    test_results, conformance_levels = None, None

    if not latest_task:
        return test_results, conformance_levels

    test_results = latest_task.test_results

    if test_results:
        _save_latest_task_results(latest_task)

        conformance_levels = ConformanceLevel.objects.filter(test_results=test_results)
        _copy_report_parameters(conformance_levels, test_results)

    _copy_latest_task_groups(latest_task, test_results, cloned_job)

    return test_results, conformance_levels


def _last_task_status_query() -> Subquery:
    return Subquery(
        Task.objects.filter(target_job=OuterRef("pk"), is_valid=True)
        .order_by("-date_started")[:1]
        .values("status")
    )


def _last_task_started_query() -> Subquery:
    return Subquery(
        Task.objects.filter(target_job=OuterRef("pk"), is_valid=True)
        .order_by("-date_started")[:1]
        .values("date_started")
    )


def _demo_user_bad_request_response(message) -> HttpResponse:
    return Response(
        data={"non_field_errors": [message]},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _copy_report_parameters(conformance_levels, test_results) -> None:
    for level in conformance_levels:
        level.pk, level.test_results = (
            None,
            test_results,
        )
        level.save()


def _save_latest_task_results(test_results) -> None:
    test_results.pk = None
    test_results.save()


def _copy_latest_task_groups(task, results, job) -> None:
    task.pk, task.test_results, task.target_job = (
        None,
        results,
        job,
    )
    task.save()


def _save_issue_screenshots(issue_example) -> None:
    for issue_screenshot in issue_example.examplescreenshot_set.all():
        issue_screenshot.pk = None
        issue_screenshot.example = issue_example
        issue_screenshot.save()


def _save_issue_examples(issue, issue_reloaded, cloned_test_results) -> None:
    for example in issue.examples.all():
        example.pk, example.issue, example.test_results = (
            None,
            issue_reloaded,
            cloned_test_results,
        )
        example.save()

        _save_issue_screenshots(example)


def _save_wcag_levels(cloned_test_results, issue_reloaded) -> None:
    conformance_level = ConformanceLevel.objects.filter(test_results=cloned_test_results, issues=issue_reloaded)

    if conformance_level.count() > 0:
        cloned_conformance_level = ConformanceLevel.objects.get(
            test_results=cloned_test_results, WCAG=conformance_level.WCAG
        )

        cloned_conformance_level.issues.add(issue_reloaded)
        cloned_conformance_level.save()


def _save_issue_parameters(test_results, cloned_test_results, wcag_levels) -> None:
    issue_related = (
        "examples",
        "examples__examplescreenshot_set",
    )

    for issue in Issue.objects.prefetch_related(*issue_related).filter(test_results=test_results):
        issue.pk, issue.test_results = (
            None,
            cloned_test_results,
        )
        issue.save()

        issue_reloaded = Issue.objects.get(pk=issue.pk)
        _save_issue_examples(issue, issue_reloaded, cloned_test_results)

        if wcag_levels:
            _save_wcag_levels(cloned_test_results, issue_reloaded)


def _save_success_criteria_levels(test_results) -> None:
    success_criteria_levels = SuccessCriteriaLevel.objects.filter(test_results=test_results)

    for success_criteria_level in success_criteria_levels:
        success_criteria_level.pk, success_criteria_level.test_results = (
            None,
            test_results,
        )
        success_criteria_level.save()
