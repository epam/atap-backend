from rest_framework import viewsets

from web_interface.api.project.permissions import get_available_projects
from web_interface.api.task_planner.serializers import PlannedTaskSerializer
from web_interface.apps.task_planner.models import PlannedTask


class PlannedTaskViewSet(viewsets.ModelViewSet):
    queryset = PlannedTask.objects.all()
    serializer_class = PlannedTaskSerializer

    def filter_queryset(self, queryset):
        queryset = queryset.filter(job__project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)
