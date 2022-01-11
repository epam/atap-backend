from abc import ABC, abstractmethod
from typing import Any, Union, List

from django.conf import settings
from django.http import HttpRequest
from rest_framework import permissions
from rest_framework.generics import GenericAPIView


class UserDemoPermissionsAPIViewABC(ABC, GenericAPIView):

    @abstractmethod
    def get_user_from_object(self, obj: Any) -> Union[settings.AUTH_USER_MODEL, List[settings.AUTH_USER_MODEL]]:
        """Receive AUTH_USER_MODEL object or objects from view"""
        pass

    def get_permissions(self) -> list:
        """Inject permissions for APIView"""
        permission_classes = list(self.permission_classes)
        permission_classes.append(UserDemoPermissions)
        return [permission() for permission in permission_classes]


class UserDemoPermissions(permissions.IsAuthenticated):

    def has_object_permission(self, request: HttpRequest, view: UserDemoPermissionsAPIViewABC, obj: Any) -> bool:
        if not self.has_permission(request, view):
            return False
        if request.user.is_demo_user:
            user = view.get_user_from_object(obj)
            if isinstance(user, list):
                return request.user in user
            else:
                return user == request.user
        return True
