from rest_framework.permissions import BasePermission

from web_interface.apps.project.models import Project


class ProjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_access_project(request.user, obj)


def can_access_project(user, project):
    """To be upgraded in the future when per-company permissions are implemented"""
    return project.users.filter(id=user.id).exists()


def get_available_projects(user):
    return Project.objects.filter(users=user)
