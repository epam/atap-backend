from typing import Union, List

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

import web_interface.apps.task.tasks
from web_interface.api.project.permissions import ProjectPermission, get_available_projects
from web_interface.api.project.serializers import (
    ExtendedProjectSerializer, SimplifiedProjectSerializer, ProjectCompaniesSerializer,
    IsSitemapRunningSerializer, GenerateSitemapSerializer, GenerateSitemapResponseSerializer, SitemapQuotaInfoSerializer
)
from web_interface.apps.auth_user.permissions import UserDemoPermissionsAPIViewABC
from web_interface.apps.project.models import Project
from web_interface.apps.framework_data.models import TestResults


class ProjectViewSet(UserDemoPermissionsAPIViewABC, viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related('users').order_by('pk')
    serializer_class = ExtendedProjectSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['company']
    ordering_fields = ['last_test', 'company', 'name', 'date_created', 'url']
    permission_classes = [ProjectPermission]

    def get_user_from_object(self, obj: Project) -> Union[settings.AUTH_USER_MODEL, List[settings.AUTH_USER_MODEL]]:
        return list(obj.users.all())

    def filter_queryset(self, queryset):
        queryset = queryset.filter(id__in=get_available_projects(self.request.user).values_list("id", flat=True))
        return super().filter_queryset(queryset)

    def perform_destroy(self, instance):
        TestResults.objects.filter(task__target_job__project=instance).delete()
        super().perform_destroy(instance)

    @swagger_auto_schema(responses={status.HTTP_200_OK: SimplifiedProjectSerializer})
    @action(methods=['GET'], detail=False, serializer_class=SimplifiedProjectSerializer, pagination_class=None)
    def simplified(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=GenerateSitemapSerializer,
                         responses={status.HTTP_200_OK: GenerateSitemapResponseSerializer,
                                    status.HTTP_400_BAD_REQUEST: GenerateSitemapSerializer})
    @action(methods=['POST'], detail=True)
    def generate_sitemap(self, request, pk=None):
        serializer = GenerateSitemapSerializer(data=request.data)
        if serializer.is_valid():
            depth_level = serializer.validated_data['depth_level']
            project = self.get_object()
            web_interface.apps.task.tasks.generate_sitemap(project.id, depth_level)
            response_serializer = GenerateSitemapResponseSerializer({'status': 'Sitemap generation started'})
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={status.HTTP_200_OK: IsSitemapRunningSerializer})
    @action(methods=['GET'], detail=True)
    def is_sitemap_running(self, request, pk=None):
        # print("*" * 60)
        # print("is_sitemap_running of ProjectViewSet")
        # print("*" * 60)
        project = self.get_object()
        serializer = IsSitemapRunningSerializer({
            'is_running': web_interface.apps.task.tasks.is_sitemap_running(project.id)
        })
        return Response(serializer.data)

    @swagger_auto_schema(responses={status.HTTP_200_OK: SitemapQuotaInfoSerializer})
    @action(methods=['GET'], detail=False)
    def sitemap_quota(self, request):
        remaining_quota = web_interface.apps.task.tasks.get_remaining_sitemap_quota()
        serializer = SitemapQuotaInfoSerializer({
            "queue_slots_available": remaining_quota,
            "can_start_sitemap": remaining_quota > 0
        })
        return Response(serializer.data)

    @swagger_auto_schema(responses={status.HTTP_200_OK: ProjectCompaniesSerializer})
    @action(methods=['GET'], detail=False)
    def companies(self, request):
        companies = Project.objects.filter(
            users__pk=request.user.pk
        ).distinct('company').values_list('company', flat=True)
        serializer = ProjectCompaniesSerializer({
            'companies': list(companies)
        })
        return Response(serializer.data)
