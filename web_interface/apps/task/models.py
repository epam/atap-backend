from django.db import models

from web_interface.apps.project.models import Project
from web_interface.apps.task import api_token
from web_interface.apps.framework_data.models import TestResults


class SitemapTask(models.Model):
    RUNNING = 'running'
    FAILED = 'failed'
    FINISHED = 'finished'
    FINISHED_WITH_PROBLEMS = 'finished_with_problems'

    STATUS_CHOICES = (
        (RUNNING, 'RUNNING'),
        (FAILED, 'FAILED'),
        (FINISHED, 'FINISHED'),
        (FINISHED_WITH_PROBLEMS, 'FINISHED_WITH_PROBLEMS')
    )
    celery_task_id = models.CharField(max_length=100, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    status = models.CharField(choices=STATUS_CHOICES, max_length=32)
    message = models.CharField(max_length=255)

    class Meta:
        db_table = 'sitemap_task'


class ActivityTask(models.Model):
    activity_task_id = models.CharField(max_length=100, null=True)
    url = models.URLField(max_length=1000)
    page_after_login = models.BooleanField(default=False)
    options = models.CharField(max_length=4000, default='')
    commands = models.CharField(max_length=4000, default='')

    class Meta:
        db_table = 'activity_task'


class Task(models.Model):
    RUNNING = 'running'
    ABORTED = 'aborted'
    CRASHED = 'crashed'
    SUCCESS = 'success'
    QUEUED = 'queued'

    STATUS_CHOICES = (
        (RUNNING, 'RUNNING'),
        (ABORTED, 'ABORTED'),
        (CRASHED, 'CRASHED'),
        (SUCCESS, 'SUCCESS'),
        (QUEUED, 'QUEUED')
    )

    date_started = models.DateTimeField(null=True)
    celery_task_id = models.CharField(max_length=100, null=True)
    target_job = models.ForeignKey('job.Job', on_delete=models.CASCADE, null=True)
    is_valid = models.BooleanField(default=True)

    status = models.CharField(choices=STATUS_CHOICES, max_length=20)
    message = models.CharField(max_length=255, blank=True)

    progress = models.CharField(max_length=2000, null=True)
    result = models.TextField(null=True)

    test_results = models.OneToOneField(TestResults, null=True, on_delete=models.CASCADE, related_name='task')
    last_reported = models.DateTimeField(null=True)
    log = models.TextField(null=True)

    @property
    def latest_report(self):
        latest_report = Report.objects.filter(task=self).latest("date_created")
        return latest_report

    class Meta:
        db_table = 'task'
        get_latest_by = 'date_started'


class Report(models.Model):
    SUCCESS = 'success'
    QUEUED = 'queued'
    GENERATING = 'generating'

    STATUS_CHOICES = (
        (SUCCESS, 'SUCCESS'),
        (QUEUED, 'QUEUED'),
        (GENERATING, 'GENERATING')
    )

    status = models.CharField(choices=STATUS_CHOICES, max_length=20)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="reports")
    delta_starting_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name="reports_starting_from")

    generated_report = models.FileField(upload_to='reports/', null=True, blank=True)
    date_created = models.DateTimeField(auto_now=True)


class WorkerKey(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    key = models.CharField(max_length=api_token.TOKEN_LENGTH * 2)

    class Meta:
        db_table = 'worker_key'
