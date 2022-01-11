from typing import Union, List

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action

from web_interface.api.page.serializers import PageSerializer
from web_interface.api.project.permissions import get_available_projects
from web_interface.apps.auth_user.permissions import UserDemoPermissionsAPIViewABC
from web_interface.apps.page.models import Page
from web_interface.apps.activity.models import Activity


class PageViewSet(UserDemoPermissionsAPIViewABC, viewsets.ModelViewSet):
    queryset = Page.objects.prefetch_related('activities').order_by('pk')
    serializer_class = PageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

    def get_user_from_object(self, obj: Page) -> Union[settings.AUTH_USER_MODEL, List[settings.AUTH_USER_MODEL]]:
        return list(obj.project.users.all())

    def filter_queryset(self, queryset):
        queryset = queryset.filter(project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    @action(methods=['GET'], detail=False, pagination_class=None)
    def entire(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        page = serializer.save()
        Activity.objects.create(name="Main Activity", click_sequence="", page=page)

