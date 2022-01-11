import base64
import json
import re
import tempfile

from django.db.models import Subquery
from django.http import FileResponse
from django_filters import DateTimeFromToRangeFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, filters, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response

from framework.report import vpat_docx_report
from web_interface.api.project.permissions import get_available_projects
from web_interface.api.report.serializers import ConformanceLevelSerializer
from web_interface.api.task import service
from web_interface.api.task.serializers import (

    TaskSerializer, ReportDownloadSerializer, AbortTaskSerializer,
    AbortTestForTaskRequestSerializer, AbortTestForTaskResponseSerializer, TasksStatusSerializer,
    TaskDownloadPieChartSerializer, SitemapTaskSerializer, StartJiraIntegrationResponseSerializer,
    GenerateReportRequestSerializer, ReportSerializer
)
from web_interface.apps.framework_data import plotter
from web_interface.apps.project.models import Project
from web_interface.apps.report.models import VpatReportParams, ConformanceLevel
from web_interface.apps.task import tasks
from web_interface.apps.task.models import Task, SitemapTask, Report
from web_interface.backend.conformance import (
    update_conformance_level, update_success_criteria_level, update_level_for_section_chapter
)


class TaskNotRunning(APIException):
    status_code = 400
    default_detail = "Cannot cancel test of a non-running task"
    default_code = "task_not_running"


class NoTestResults(APIException):
    status_code = 400
    default_detail = "Cannot download pie chart - no test results for this task"
    default_code = "no_test_results"


class SitemapTaskViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = SitemapTask.objects.all()
    serializer_class = SitemapTaskSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project']
    ordering_fields = ['project']

    @action(methods=['POST'], detail=True)
    def abort_task(self, request: Request, pk: int):
        sitemap_task = self.get_object()
        service.abort_sitemap_task(sitemap_task)
        serializer = AbortTaskSerializer({'status': 'Sitemap task aborted'})
        return Response(serializer.data)

class TaskViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Task.objects.select_related('target_job', 'target_job__project').order_by('pk')
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['target_job__project']
    ordering_fields = ['date_started', 'name', 'target_job__name', 'target_job__project__name', 'date_started']

    def filter_queryset(self, queryset):
        queryset = queryset.filter(target_job__project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    @swagger_auto_schema(request_body=no_body,
                         responses={status.HTTP_200_OK: AbortTaskSerializer})
    @action(methods=['POST'], detail=True)
    def abort_task(self, request, pk=None):
        task = self.get_object()
        tasks.abort_task(task)
        serializer = AbortTaskSerializer({'status': 'Task Aborted'})
        return Response(serializer.data)

    @swagger_auto_schema(request_body=no_body,
                         responses={status.HTTP_200_OK: ConformanceLevelSerializer(many=True)})
    @action(methods=['POST'], detail=True)
    def recalculate_wcag(self, request, pk=None):
        task = self.get_object()
        update_conformance_level(task.test_results)
        update_success_criteria_level(task.test_results)
        update_level_for_section_chapter(task.test_results, section='508', chapter='3')
        update_level_for_section_chapter(task.test_results, section='EN', chapter='4')
        conformance_levels_qs = ConformanceLevel.objects.prefetch_related('issues').filter(
            test_results=task.test_results
        )

        serializer = ConformanceLevelSerializer(conformance_levels_qs, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=AbortTestForTaskRequestSerializer,
                         responses={status.HTTP_200_OK: AbortTestForTaskResponseSerializer})
    @action(methods=['POST'], detail=True)
    def abort_test_for_task(self, request, pk=None):
        serializer = AbortTestForTaskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        task = self.get_object()
        if task.status != Task.RUNNING:
            raise TaskNotRunning()
        tasks.cancel_test_for_task(task_id=task.id, test_name=validated_data['test_name'])
        serializer = AbortTestForTaskResponseSerializer({'status': 'Test for Task Aborted'})
        return Response(serializer.data)

    @swagger_auto_schema(responses={status.HTTP_200_OK: TasksStatusSerializer})
    @action(methods=['GET'], detail=False,
            filter_backends=(), filterset_fields=None, ordering_fields=None, pagination_class=None)
    def get_status(self, request, pk=None):
        tasks.verify_tasks_running()
        projects = Project.objects.filter(users=request.user)
        global_task_qs = Task.objects.select_related('target_job', 'target_job__project')
        all_queued_count = Task.objects.filter(status=Task.QUEUED).count()
        if request.user.groups.filter(name='Admin').exists():
            running_tasks = global_task_qs.filter(status=Task.RUNNING).order_by('-date_started')
            queued_tasks = global_task_qs.filter(status=Task.QUEUED).order_by('date_started')
        else:
            running_tasks = global_task_qs.filter(
                status=Task.RUNNING, target_job__project__in=Subquery(projects.values('id'))
            ).order_by('-date_started')
            queued_tasks = global_task_qs.filter(
                status=Task.QUEUED, target_job__project__in=Subquery(projects.values('id'))
            ).order_by('date_started')

        data = {
            'running_tasks': [],
            'queue_data': [],
            'all_queued_count': all_queued_count
        }

        for running_task in running_tasks:
            progress_json = running_task.progress
            if progress_json is None:
                cur_progress = {
                    'overall_progress': 'Starting...',
                    'thread_count': 0,
                    'thread_status': {},
                    'thread_task_cancellable': {},
                    'thread_test_name': {},
                    'thread_time_started': {},
                    'tasks_complete': 0,
                    'tasks_count': 1
                }
            else:
                try:
                    cur_progress = json.loads(progress_json)
                except json.JSONDecodeError:
                    print(f'Failed to decode \'{progress_json}\'')
                    cur_progress = {
                        'overall_progress': 'ERROR: Cannot decode task progress!',
                        'thread_count': 0,
                        'thread_status': {},
                        'thread_task_cancellable': {},
                        'thread_test_name': {},
                        'thread_time_started': {},
                        'tasks_complete': 0,
                        'tasks_count': 1
                    }

            task_data = {
                'task_id': running_task.id,
                'job_id': running_task.target_job.id,
                'project_id': running_task.target_job.project.id,
                'progress': cur_progress
            }
            data['running_tasks'].append(task_data)

        for queued_task in queued_tasks:
            data['queue_data'].append(
                {
                    'task_id': queued_task.id,
                    'job_id': queued_task.target_job.id,
                    'job_name': queued_task.target_job.name,
                    'project_id': queued_task.target_job.project.id,
                    'project_name': queued_task.target_job.project.name,
                    'date_started': queued_task.date_started
                }
            )
        serializer = TasksStatusSerializer(data)
        return Response(serializer.data)

    # responses={status.HTTP_200_OK: TaskReportGenerationResponseSerializer}
    @swagger_auto_schema(request_body=GenerateReportRequestSerializer)
    @action(methods=['POST'], detail=True)
    def generate_audit_report(self, request, pk=None):
        serializer = GenerateReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        if validated_data["is_delta_report"]:
            tasks.regenerate_report(self.get_object(), Task.objects.get(id=validated_data["delta_starting_task"]))
        else:
            tasks.regenerate_report(self.get_object(), None)
        return Response()

    @swagger_auto_schema(responses={status.HTTP_200_OK: TaskDownloadPieChartSerializer})
    @action(methods=['GET'], detail=True)
    def download_pie_chart(self, request, pk=None):
        task = self.get_object()
        test_results = task.test_results
        if test_results is None:
            raise NoTestResults

        name = f'{task.target_job.project.name}'
        extension = '.png'
        pie_chart_file, alttext = plotter.draw_pie_chart(test_results)

        filename = f'{name}_{task.date_started}{extension}'
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)

        pie_chart_file.seek(0)
        method = request.GET.get('method')
        if method == 'file':
            response = FileResponse(pie_chart_file, filename=filename)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'
            return response

        pie_chart_data = base64.b64encode(pie_chart_file.read()).decode()
        serializer = TaskDownloadPieChartSerializer({
            'status': 'Pie Chart Generated',
            'filename': filename,
            'alttext': alttext,
            'image': pie_chart_data
        })
        return Response(serializer.data)

    @swagger_auto_schema(responses={status.HTTP_200_OK: ReportDownloadSerializer})
    @action(methods=['GET'], detail=True)
    def download_vpat_report(self, request, pk=None):
        task = self.get_object()
        report_params = VpatReportParams.objects.get(id=request.GET['vpat_report_id'])

        name = f'{task.target_job.project.name} {report_params.name}'
        extension = '.docx'
        report_file = tempfile.NamedTemporaryFile()
        vpat_docx_report.VpatReport(
            task=task,
            report_params=report_params,
        ).create(report_file.name)

        report_file.seek(0)
        filename = f'{name}_{task.date_started}{extension}'
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)

        method = request.GET.get('method')
        if method == 'file':
            response = FileResponse(report_file, filename=filename)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'
            return response

        data = base64.b64encode(report_file.read())
        serializer = ReportDownloadSerializer({
            'status': 'Report Generated',
            'filename': filename,
            'report': data
        })
        return Response(serializer.data)

    @swagger_auto_schema(responses={status.HTTP_200_OK: StartJiraIntegrationResponseSerializer})
    @action(methods=['POST'], detail=True)
    def start_jira_integration(self, request, pk=None):
        task = self.get_object()
        jira_integration_params = task.target_job.project.jira_integration_params
        if not jira_integration_params:
            serializer = StartJiraIntegrationResponseSerializer({
                "success": False,
                "message": "Jira integration params don't exist for parent project"
            })
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        tasks.create_examples_in_jira(jira_integration_params, task)
        serializer = StartJiraIntegrationResponseSerializer({
            "success": True,
            "message": "Jira task creation started"
        })
        return Response(serializer.data)


class TaskReportsFilter(FilterSet):
    date_created = DateTimeFromToRangeFilter()

    class Meta:
        model = Report
        fields = ['status', 'task', 'delta_starting_task', 'date_created', 'task__target_job__name', 'task__target_job__id', 'task__target_job__project__id', 'task__date_started']


class TaskReportsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.select_related("task", "task__target_job", "task__target_job__project").order_by('-date_created')
    serializer_class = ReportSerializer
    filter_class = TaskReportsFilter
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'task', 'delta_starting_task', 'date_created', 'task__target_job__name', 'task__target_job__id', 'task__target_job__project__id', 'task__date_started']
    ordering_fields = ['status', 'task', 'delta_starting_task', 'date_created']

    def filter_queryset(self, queryset):
        queryset = queryset.filter(task__target_job__project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    @swagger_auto_schema(responses={status.HTTP_200_OK: ReportDownloadSerializer})
    @action(methods=['GET'], detail=True)
    def download(self, request, pk=None):
        report = self.get_object()

        report_file = report.generated_report

        report_file.open(mode='rb')
        method = request.GET.get('method')
        if method == "file":
            response = FileResponse(report_file, filename=report_file.name)
            response['Content-Disposition'] = f'attachment; filename="{report_file.name}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'
            return response

        data = base64.b64encode(report_file.read())
        serializer = ReportDownloadSerializer({
            'status': 'Report Generated',
            'filename': report_file.name,
            'report': data
        })
        report_file.close()
        return Response(serializer.data)
