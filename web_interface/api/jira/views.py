from typing import Union, List

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework import status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from jira import JIRA, JIRAError

from web_interface.api.jira.serializers import JiraIntegrationParamsSerializer, JiraValidationSerializer, \
    JiraValidationResponseSerializer
from web_interface.api.project.permissions import get_available_projects
from web_interface.apps.jira.models import JiraIntegrationParams
from web_interface.apps.auth_user.permissions import UserDemoPermissionsAPIViewABC


class JiraIntegrationParamViewSet(UserDemoPermissionsAPIViewABC, viewsets.ModelViewSet):
    queryset = JiraIntegrationParams.objects.all()
    serializer_class = JiraIntegrationParamsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project']
    ordering_fields = ['project']

    def filter_queryset(self, queryset):
        queryset = queryset.filter(project__in=get_available_projects(self.request.user))
        return super().filter_queryset(queryset)

    def get_user_from_object(self, obj: JiraIntegrationParams) -> Union[settings.AUTH_USER_MODEL, List[settings.AUTH_USER_MODEL]]:
        return list(obj.project.users.all())


class JiraValidationAPIView(APIView):

    @swagger_auto_schema(request_body=JiraValidationSerializer,
                         responses={status.HTTP_200_OK: JiraValidationResponseSerializer,
                                    status.HTTP_400_BAD_REQUEST: JiraValidationSerializer,
                                    status.HTTP_401_UNAUTHORIZED: JiraValidationSerializer})
    def post(self, request, format=None):
        serializer = JiraValidationSerializer(data=request.data)
        if serializer.is_valid():
            host = serializer.validated_data['host']
            username = serializer.validated_data['username']
            token = serializer.validated_data['token']
            try:
                JIRA(server=host, basic_auth=(username, token))
                return Response(JiraValidationResponseSerializer({"is_valid": True, "message": "ok"}).data)
            except JIRAError:
                return Response(JiraValidationResponseSerializer({"is_valid": False, "message": "JIRA authorization params are invalid"}).data, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
