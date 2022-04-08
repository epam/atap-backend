from typing import Optional

from django.db import models
from django.conf import settings
from django.db.models import Q

from web_interface.apps.page.models import Page
from web_interface.apps.project.models import Project
from web_interface.apps.task.models import Task


class Job(models.Model):
    name = models.CharField(max_length=1000, default="Test Job")
    date_created = models.DateTimeField(auto_now=True)
    project = models.ForeignKey(Project, related_name="jobs", on_delete=models.CASCADE)
    pages = models.ManyToManyField(Page)
    # TODO refactor 'test_list' field. Add as M2M field with related name to AvailableTest model
    test_list = models.CharField(max_length=4000, default="")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    last_test = models.DateTimeField(null=True, blank=True)
    resolutions = models.CharField(max_length=4000, default="")
    estimated_testing_time = models.IntegerField(null=True)

    class Meta:
        db_table = "job"

    def __str__(self):
        return (
            f"{self.__class__.__name__} object "
            f"(id: {self.id}) (name: {self.name}) (project_id: {self.project_id})"
        )

    def status(self) -> str:
        running_qs = self.task_set.filter(is_valid=True, status=Task.RUNNING)
        queued_qs = self.task_set.filter(is_valid=True, status=Task.QUEUED)
        if queued_qs.exists():
            return "In queue"
        elif running_qs.exists():
            return "In progress"
        else:
            return "Completed"

    def get_last_task(self, task_status: Optional[str] = None) -> Optional["Task"]:
        filter_body = Q(is_valid=True)
        if task_status:
            filter_body &= Q(status=task_status)
        return self.task_set.filter(filter_body).order_by("date_started").last()
