from typing import Union, List

import django_filters
from django.conf import settings
from django.db.models import Subquery, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from web_interface.api.job.serializers import (
    JobSerializer, JobTaskSerializer, PrecalculateJobRequestSerializer, PrecalculateJobResponseSerializer,
    SimplifiedJobSerializer
)
from web_interface.api.project.permissions import get_available_projects
from web_interface.apps.auth_user.permissions import UserDemoPermissionsAPIViewABC
from web_interface.apps.job.models import Job
from web_interface.apps.project.models import Project
from web_interface.apps.report.models import ConformanceLevel, Issue, SuccessCriteriaLevel
from web_interface.apps.task import tasks
from web_interface.apps.task.models import Task


class ListFilter(django_filters.Filter):
    def filter(self, qs, value):
        if not value:
            return qs

        self.lookup_expr = 'in'
        values = value.split(',')
        return super(ListFilter, self).filter(qs, values)


class JobAPIFilter(django_filters.FilterSet):

    project = django_filters.ModelChoiceFilter(queryset=Project.objects.all())
    task_status = ListFilter(field_name="last_task_status", label="Task Status")

    ordering = django_filters.OrderingFilter(
        fields=(
            ('name', 'name'),
            ('project__name', 'project_name'),
            ('last_task_status', 'task_status'),
            ('last_test', 'last_test'),
        ),
    )

    class Meta:
        model = Job
        fields = ('project',)


class JobViewSet(UserDemoPermissionsAPIViewABC, viewsets.ModelViewSet):
    queryset = Job.objects.select_related(
        'project'
    ).prefetch_related(
        'task_set', 'vpatreportparams_set', 'pages'
    ).annotate(
        last_task_status=Subquery(
            Task.objects.filter(
                target_job=OuterRef('pk'),
                is_valid=True
            ).order_by('-date_started')[:1].values('status')
        ),
        last_task_started=Subquery(
            Task.objects.filter(
                target_job=OuterRef('pk'),
                is_valid=True
            ).order_by('-date_started')[:1].values('date_started')
        )
    ).order_by('last_task_started')
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
        for task in tasks_qs:
            tasks.abort_task(task)
        super().perform_destroy(instance)

    @swagger_auto_schema(responses={status.HTTP_200_OK: SimplifiedJobSerializer})
    @action(methods=['GET'], detail=False, serializer_class=SimplifiedJobSerializer, pagination_class=None)
    def simplified(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=PrecalculateJobRequestSerializer,
                         responses={status.HTTP_200_OK: PrecalculateJobResponseSerializer,
                                    status.HTTP_400_BAD_REQUEST: PrecalculateJobRequestSerializer})
    @action(methods=['POST'], detail=False)
    def precalculate_job_length(self, request, pk=None):
        serializer = PrecalculateJobRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        time = tasks.precalculate_job_length(
            data['tests'],
            data['pages']
        )
        response_serializer = PrecalculateJobResponseSerializer({'time': time})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=no_body, responses={status.HTTP_200_OK: JobTaskSerializer,
                                                          status.HTTP_400_BAD_REQUEST: JobTaskSerializer})
    @action(methods=['POST'], detail=True)
    def start_task(self, request, pk=None):
        if request.user.is_demo_user:
            running_jobs_count = Job.objects.filter(
                project__users=request.user,
                task__status__in=(Task.QUEUED, Task.RUNNING)
            ).distinct().count()
            if running_jobs_count >= request.user.demo_permissions.running_jobs_quota:
                return Response(
                    data={
                        'non_field_errors': [
                            'The quota for execution jobs has been exceeded. '
                            'Contact your administrator to change your subscription plan.'
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        job = self.get_object()
        task_id = tasks.request_test_for_job(job)['task_id']
        if task_id == -1:
            return Response(
                data={
                    'non_field_errors': [
                        'Task already in queue for this job'
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = JobTaskSerializer(Task.objects.get(id=task_id))
        return Response(serializer.data)

    @swagger_auto_schema(request_body=no_body, responses={status.HTTP_200_OK: JobSerializer,
                                                          status.HTTP_400_BAD_REQUEST: JobSerializer})
    @action(methods=['POST'], detail=True)
    def clone(self, request, pk=None):
        if request.user.is_demo_user:
            jobs_created_count = Job.objects.filter(project__users=request.user).count()
            if jobs_created_count >= request.user.demo_permissions.jobs_quota:
                return Response(
                    data={
                        'non_field_errors': [
                            'The quota for creating (over cloning) jobs has been exceeded. '
                            'Contact your administrator to change your subscription plan.'
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        old_job = self.get_object()

        new_job = Job.objects.get(pk=old_job.pk)
        new_job.pk = None
        new_job.name = f'{new_job.name} (Copy)'
        new_job.save()

        test_results = None
        conformance_levels = None
        latest_task = Task.objects.filter(target_job=old_job).latest()

        if latest_task:
            latest_task.pk = None
            test_results = latest_task.test_results
            if test_results:
                test_results.pk = None
                test_results.save()

                # Copying report params...
                conformance_levels = ConformanceLevel.objects.filter(test_results=test_results)
                for level in conformance_levels:
                    level.pk = None
                    level.test_results = test_results
                    level.save()

            latest_task.test_results = test_results
            latest_task.target_job = new_job
            latest_task.save()

        try:
            old_test_results = Task.objects.filter(target_job=old_job).latest().test_results
        except AttributeError:
            pass
        else:
            # Copying issue groups...
            for issue in Issue.objects.prefetch_related(
                    'examples', 'examples__examplescreenshot_set'
            ).filter(test_results=old_test_results):
                issue.pk = None
                issue.test_results = test_results
                issue.save()
                issue_reloaded = Issue.objects.get(pk=issue.pk)
                for example in issue.examples.all():
                    example.issue = issue_reloaded
                    example.pk = None
                    example.test_results = test_results
                    example.save()
                    for issue_screenshot in example.examplescreenshot_set.all():
                        issue_screenshot.pk = None
                        issue_screenshot.example = example
                        issue_screenshot.save()

                if conformance_levels:
                    old_conformance_level = ConformanceLevel.objects.filter(
                        test_results=test_results,
                        issues=issue_reloaded
                    )
                    if old_conformance_level.count() > 0:
                        conformance_level = ConformanceLevel.objects.get(
                            test_results=test_results,
                            WCAG=old_conformance_level.WCAG
                        )
                        conformance_level.issues.add(issue_reloaded)
                        conformance_level.save()

            success_criteria_levels = SuccessCriteriaLevel.objects.filter(test_results=old_test_results)
            for success_criteria_level in success_criteria_levels:
                success_criteria_level.test_results = test_results
                success_criteria_level.pk = None
                success_criteria_level.save()

        serializer = self.get_serializer(new_job)
        return Response(serializer.data)
