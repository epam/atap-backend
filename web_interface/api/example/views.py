from django.db.models import QuerySet
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from framework import xlsdata
from web_interface.api.example.serializers import (
    ExampleSerializer, IssueSerializer, IssueForWarnSerializer, ExampleScreenshotSerializer, IssuePrioritiesSerializer,
    IssueLabelsSerializer
)
from web_interface.api.project.permissions import get_available_projects
from web_interface.apps.issue.example_manipulation import find_issue_for_warn, create_new_issue
from web_interface.apps.issue.models import Example, ExampleScreenshot
from web_interface.apps.report.models import Issue


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.order_by('pk')
    serializer_class = IssueSerializer

    def filter_queryset(self, queryset):
        queryset = queryset.filter(test_results__task__target_job__project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    @action(methods=['GET'], detail=False, pagination_class=None)
    def priorities(self, request, pk=None):
        priorities = ["Blocker", "Critical", "Major", "Minor"]
        serializer = IssuePrioritiesSerializer(priorities)
        return Response(serializer.data)

    @action(methods=['GET'], detail=False, pagination_class=None)
    def labels(self, request, pk=None):
        label_lists = [item['labels'] for item in xlsdata.cached_problem_type_data.values()]
        labels = set([item for label_list in label_lists for item in label_list])
        serializer = IssueLabelsSerializer(labels)
        return Response(serializer.data)


class ExampleViewSet(viewsets.ModelViewSet):
    queryset = Example.objects.order_by('pk')
    serializer_class = ExampleSerializer

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        available_projects = get_available_projects(self.request.user)
        return queryset.filter(test_results__task__target_job__project__in=available_projects)

    @action(methods=['GET'], detail=True)
    def metadata(self, request: Request, pk=None):
        example = self.get_object()
        data = xlsdata.get_data_for_issue(example.err_id)
        return Response(data)

    @swagger_auto_schema(request_body=IssueForWarnSerializer,
                         responses={status.HTTP_200_OK: IssueSerializer,
                                    status.HTTP_400_BAD_REQUEST: IssueForWarnSerializer})
    @action(methods=['POST'], detail=True)
    def find_issue_for_warn(self, request: Request, pk=None):
        serializer = IssueForWarnSerializer(data=request.data)
        if serializer.is_valid():
            is_best_practice = serializer.validated_data['is_best_practice']
            example = self.get_object()
            issue = find_issue_for_warn(
                err_id=example.err_id, is_best_practice=is_best_practice, task=example.test_results.task
            )
            if not issue:
                issue = create_new_issue(
                    err_id=example.err_id, task=example.test_results.task, force_best_practice=is_best_practice)
            serializer = IssueSerializer(issue)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExampleScreenshotViewSet(mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.DestroyModelMixin,
                               mixins.ListModelMixin,
                               mixins.UpdateModelMixin,
                               GenericViewSet):
    queryset = ExampleScreenshot.objects.order_by('pk')
    serializer_class = ExampleScreenshotSerializer
