import os

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from framework.libs.basic_groups import BASED_TEST_HARDCODE
from web_interface.api.framework_data import service
from web_interface.api.framework_data.serializers import (
    TestResultSerializer,
    AvailableTestSerializer,
    AvailableTestGroupSerializer, TestTimingSerializer,
)
from web_interface.api.project.permissions import get_available_projects
from web_interface.apps.framework_data.models import TestResults, AvailableTest, AvailableTestGroup, TestTiming


class TestResultsViewSet(viewsets.ReadOnlyModelViewSet):
    def filter_queryset(self, queryset):
        queryset = queryset.filter(task__target_job__project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    queryset = TestResults.objects.order_by("pk")
    serializer_class = TestResultSerializer


class AvailableTestViewSet(viewsets.ReadOnlyModelViewSet):
    """Only verified and working tests are available on Production environment!"""

    if os.environ.get("CURRENT_ENV") in ("PROD", "PROD_DEBUG"):
        queryset = AvailableTest.objects.filter(
            Q(name__in=BASED_TEST_HARDCODE) | ~Q(name__startswith="test")
        ).order_by("pk")
    else:
        queryset = AvailableTest.objects.order_by("pk")
    serializer_class = AvailableTestSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["groups"]


class AvailableTestGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableTestGroup.objects.order_by("pk")
    serializer_class = AvailableTestGroupSerializer
    pagination_class = None


class TestTimingView(viewsets.ModelViewSet):
    queryset = TestTiming.objects.all()

    @swagger_auto_schema(responses={status.HTTP_200_OK: TestTimingSerializer})
    @action(methods=["POST"], detail=False)
    def predict(self, request: Request):
        serializer = TestTimingSerializer(data=request.data)
        if serializer.is_valid():
            prediction = service.get_prediction(list(serializer.validated_data.values()))
            return Response(prediction)
        else:
            return Response(serializer.errors)
