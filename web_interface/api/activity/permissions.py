from rest_framework.permissions import BasePermission
from web_interface.api.project.permissions import can_access_project


class ActivityPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_access_project(request.user, obj.page.project)
