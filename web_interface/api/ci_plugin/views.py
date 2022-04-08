from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from web_interface.apps.task import tasks
from web_interface.apps.task.task_functional import callback_progress
from web_interface.api.ci_plugin.serializers import (
    CIPluginJobSerializer,
    CIPluginTaskSerializer,
    CIPluginJobTaskSerializer,
    CIPluginAbortTaskTaskSerializer,
)
from web_interface.apps.api_key.permissions import HasKeyForProjectViewABC
from web_interface.apps.job.models import Job
from web_interface.apps.project.models import Project
from web_interface.apps.task.models import Task


class CIPluginJobViewSet(HasKeyForProjectViewABC, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = Job.objects.select_related("project")
    serializer_class = CIPluginJobSerializer

    def check_post_access(self, request, project) -> bool:
        return True

    def get_access_project(self, obj) -> Project:
        return obj.project

    @swagger_auto_schema(request_body=no_body, responses={status.HTTP_200_OK: CIPluginJobTaskSerializer})
    @action(methods=["POST"], detail=True)
    def start_task(self, request, pk=None):
        job = self.get_object()
        task_id = callback_progress.request_test_for_job(job)["task_id"]
        serializer = CIPluginJobTaskSerializer(Task.objects.get(id=task_id))
        return Response(serializer.data)


class CIPluginTaskViewSet(HasKeyForProjectViewABC, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = Task.objects.select_related("target_job__project", "test_results").prefetch_related(
        "test_results__test_set"
    )
    serializer_class = CIPluginTaskSerializer

    def check_post_access(self, request, project) -> bool:
        return True

    def get_access_project(self, obj) -> Project:
        return obj.target_job.project

    @swagger_auto_schema(request_body=no_body, responses={status.HTTP_200_OK: CIPluginAbortTaskTaskSerializer})
    @action(methods=["POST"], detail=True)
    def abort_task(self, request, pk=None):
        tasks.abort_task(self.get_object())
        serializer = CIPluginAbortTaskTaskSerializer({"status": "Task Aborted"})
        return Response(serializer.data)
