from django.db import models

from web_interface.apps.project.models import Project
from web_interface.apps.task.models import Task


class JiraIntegrationParams(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="jira_integration_params")
    host = models.CharField(max_length=1000)
    username = models.CharField(max_length=256)
    token = models.CharField(max_length=512)
    jira_project_key = models.CharField(max_length=128)

    class Meta:
        db_table = 'jira_integration'


class JiraRootIssue(models.Model):
    jira_integration = models.ForeignKey(JiraIntegrationParams, on_delete=models.CASCADE)
    error_id = models.CharField(max_length=64)
    jira_task_key = models.CharField(max_length=128)
    added_examples = models.ManyToManyField('issue.Example')

    class Meta:
        db_table = 'jira_root_issue'


class JiraWorkerTask(models.Model):
    RUNNING = 'running'
    FAILED = 'failed'
    SUCCESS = 'success'
    QUEUED = 'queued'

    STATUS_CHOICES = (
        (RUNNING, 'RUNNING'),
        (FAILED, 'FAILED'),
        (SUCCESS, 'SUCCESS'),
        (QUEUED, 'QUEUED'),
    )

    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='jira_worker_task')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=QUEUED)
    message = models.CharField(max_length=255, blank=True, default='')
    total_examples = models.IntegerField(default=0)
    processed_examples = models.IntegerField(default=0)
    total_issues = models.IntegerField(default=0)
    reopened_issues = models.IntegerField(default=0)
    duplicated_issues = models.IntegerField(default=0)
