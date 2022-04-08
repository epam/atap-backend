from typing import Union, List

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema, no_body

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from web_interface.api.job.filters import JobAPIFilter
from web_interface.api.job.serializers import (
    JobSerializer,
    JobTaskSerializer,
    EstimateJobTimeRequestSerializer,
    EstimateJobTimeResponseSerializer,
    SimplifiedJobSerializer,
)
from web_interface.api.project.permissions import get_available_projects
from web_interface.apps.auth_user.permissions import UserDemoPermissionsAPIViewABC
from web_interface.apps.job.models import Job
from web_interface.apps.task.models import Task
from web_interface.apps.task.task_functional import callback_progress
from web_interface.api.job.job_services import (
    jobs_sorted_ran_last_query,
    abort_job_tasks,
    get_calculated_job_time,
    get_estimated_job_time,
    running_jobs_query,
    created_jobs_number_query,
    demo_subscription_ended_response,
    task_queued_response,
    create_job_clone,
    save_latest_task,
    copy_cloned_job_groups,
)


class JobViewSet(UserDemoPermissionsAPIViewABC, viewsets.ModelViewSet):
    queryset = jobs_sorted_ran_last_query()
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = JobAPIFilter

    def get_user_from_object(self, obj: Job) -> Union[settings.AUTH_USER_MODEL, List[settings.AUTH_USER_MODEL]]:
        return list(obj.project.users.all())

    def filter_queryset(self, queryset):
        queryset = queryset.filter(project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    def perform_destroy(self, instance):
        tasks_qs = instance.task_set.filter(status__in=(Task.QUEUED, Task.RUNNING), is_valid=True)
        abort_job_tasks(tasks_qs)
        super().perform_destroy(instance)

    @swagger_auto_schema(responses={status.HTTP_200_OK: SimplifiedJobSerializer})
    @action(methods=["GET"], detail=False, serializer_class=SimplifiedJobSerializer, pagination_class=None)
    def simplified(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=EstimateJobTimeRequestSerializer,
        responses={
            status.HTTP_200_OK: EstimateJobTimeResponseSerializer,
            status.HTTP_400_BAD_REQUEST: EstimateJobTimeRequestSerializer,
        },
    )
    @action(methods=["POST"], detail=False)
    def get_mean_job_test_time(self, request, pk=None):
        serializer = EstimateJobTimeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job_best_guess_time = get_calculated_job_time(serializer)
        response_serializer = EstimateJobTimeResponseSerializer({"time": job_best_guess_time})

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=EstimateJobTimeRequestSerializer,
        responses={
            status.HTTP_200_OK: EstimateJobTimeResponseSerializer,
            status.HTTP_400_BAD_REQUEST: EstimateJobTimeRequestSerializer,
        },
    )
    @action(methods=["POST"], detail=False)
    def estimate_job_test_time(self, request, pk=None):
        serializer = EstimateJobTimeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job_trained_model_estimated_time = get_estimated_job_time(serializer)
        response_serializer = EstimateJobTimeResponseSerializer({"time": job_trained_model_estimated_time})

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=no_body,
        responses={status.HTTP_200_OK: JobTaskSerializer, status.HTTP_400_BAD_REQUEST: JobTaskSerializer},
    )
    @action(methods=["POST"], detail=True)
    def start_task(self, request, pk=None):
        if request.user.is_demo_user:
            # * check demo limit
            try:
                return demo_subscription_ended_response(request, running_jobs_query)
            except NameError:
                pass

        job = self.get_object()
        task_id = callback_progress.request_test_for_job(job)["task_id"]
        print("task_id", task_id)

        try:
            return task_queued_response(task_id)
        except NameError:
            serializer = JobTaskSerializer(Task.objects.get(id=task_id))

        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=no_body,
        responses={status.HTTP_200_OK: JobSerializer, status.HTTP_400_BAD_REQUEST: JobSerializer},
    )
    @action(methods=["POST"], detail=True)
    def clone(self, request, pk=None):
        if request.user.is_demo_user:
            try:
                demo_subscription_ended_response(request, created_jobs_number_query)
            except NameError:
                pass

        old_job = self.get_object()
        new_job = create_job_clone(old_job)
        test_results, conformance_levels = save_latest_task(old_job, new_job)

        copy_cloned_job_groups(old_job, test_results, conformance_levels)

        serializer = self.get_serializer(new_job)

        return Response(serializer.data)
