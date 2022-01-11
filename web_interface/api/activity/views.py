from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action

from web_interface.api.activity.permissions import ActivityPermission
from web_interface.api.activity.serializers import ActivitySerializer, ActivityValidationSerializer
from web_interface.api.project.permissions import get_available_projects
from web_interface.apps.activity.models import Activity
from rest_framework.response import Response
from web_interface.apps.task import tasks
from django.db import transaction


class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.order_by('pk')
    serializer_class = ActivitySerializer

    def filter_queryset(self, queryset):
        queryset = queryset.filter(page__project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    @swagger_auto_schema(request_body=ActivitySerializer, responses={status.HTTP_200_OK: ActivityValidationSerializer})
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def verify_activity(self, request):
        serializer = ActivitySerializer(data=request.data)
        if serializer.is_valid():
            activity_to_test = serializer.create(serializer.validated_data)
            result, error = tasks.verify_activity(activity_to_test)
            activity_to_test.delete()
            return Response({"is_valid": result, "message": error})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
