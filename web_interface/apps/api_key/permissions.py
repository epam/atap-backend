from abc import ABC, abstractmethod
from typing import Any

from django.http import HttpRequest
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ViewSetMixin
from rest_framework_api_key.permissions import BaseHasAPIKey

from web_interface.apps.api_key.models import CheckerAPIKey
from web_interface.apps.project.models import Project


class IsAdminUserExtended(IsAdminUser):
    def has_object_permission(self, request, view, obj):
        """Return `True` if permission is granted, `False` otherwise."""
        if not self.has_permission(request, view):
            return False
        return True


class HasKeyForProjectViewABC(ABC, ViewSetMixin):

    @abstractmethod
    def check_post_access(self, request: HttpRequest, project: Project) -> bool:
        """Check post access for view"""
        pass

    @abstractmethod
    def get_access_project(self, obj) -> Project:
        """Receive Project object from view"""
        pass

    def get_permissions(self):
        """List always will be blocked because of Jenkins usage"""
        permission_classes = [IsAdminUserExtended]
        if self.action != 'list':
            permission_classes = [IsAdminUserExtended | HasKeyForProject]
        return [permission() for permission in permission_classes]


class HasKeyForProject(BaseHasAPIKey):
    model = CheckerAPIKey
    message = 'API Key invalid'

    def has_permission(self, request: HttpRequest, view: HasKeyForProjectViewABC) -> bool:
        assert self.model is not None, (
                '%s must define `.model` with the API key model to use'
                % self.__class__.__name__
        )
        key = self.get_key(request)
        if not key:
            return False
        if not self.model.objects.is_valid(key):
            return False
        key_object = self.model.objects.get_from_key(key)
        return request.method != 'POST' or view.check_post_access(request, key_object.project)

    def has_object_permission(self, request: HttpRequest, view: HasKeyForProjectViewABC, obj: Any) -> bool:
        key_object = self.model.objects.get_from_key(self.get_key(request))

        if not self.has_permission(request, view):
            return False

        return view.get_access_project(obj) == key_object.project
