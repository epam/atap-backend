from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from framework import xlsdata
from framework.xlsdata import (
    cached_references,
    cached_wcag_table_info,
    cached_problem_type_data,
    cached_sr_versions,
    cached_vpat_data,
    cached_wcag_test_matching,
)
from web_interface.api.helpers.serializers import (
    UrlValidationSerializer,
    UrlValidationResponseSerializer,
    ApplicationInfoResponseSerializer,
    FrameworkMetadataResponseSerializer,
    AuthValidationSerializer,
    AuthValidationResponseSerializer,
)
from web_interface.backend import url_checker
from web_interface.backend.authentication_checker import AuthenticationChecker

import shutil


class UrlValidationAPIView(APIView):
    @swagger_auto_schema(
        request_body=UrlValidationSerializer,
        responses={
            status.HTTP_200_OK: UrlValidationResponseSerializer,
            status.HTTP_400_BAD_REQUEST: UrlValidationSerializer,
        },
    )
    def post(self, request, format=None):
        serializer = UrlValidationSerializer(data=request.data)
        if serializer.is_valid():
            validated_url = serializer.validated_data["url"]
            check_url_response = url_checker.check_url(validated_url)
            response_serializer = UrlValidationResponseSerializer(check_url_response)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthValidationAPIView(APIView):
    @swagger_auto_schema(
        request_body=AuthValidationSerializer,
        responses={
            status.HTTP_200_OK: AuthValidationResponseSerializer,
            status.HTTP_400_BAD_REQUEST: AuthValidationSerializer,
        },
    )
    def post(self, request, format=None):
        # print("*" * 60)
        # print("*" * 60)
        # print("post AuthValidationAPIView")
        # print("*" * 60)
        # print("*" * 60)
        serializer = AuthValidationSerializer(data=request.data)
        # print("serializer AuthValidationSerializer")
        if serializer.is_valid():
            # print("serializer.is_valid")
            validated_url = serializer.validated_data["url"]
            validated_type = serializer.validated_data["auth_type"]
            validated_auth_setting = serializer.validated_data["auth_setting"]
            # print("validated_url", validated_url)
            # print("validated_type", validated_type)
            # print("validated_auth_setting", validated_auth_setting)
            check_auth_response = AuthenticationChecker(
                validated_url, validated_type, validated_auth_setting
            ).execute()
            # print("****************************")
            # print("in AuthValidationAPIView")
            # print("check_auth_response", check_auth_response)
            response_serializer = AuthValidationResponseSerializer(
                {"is_valid": check_auth_response.is_valid, "message": check_auth_response.message}
            )
            # print("response_serializer", response_serializer.data)
            # print("RETURN VALID", response_serializer.data)
            return Response(response_serializer.data)
        # print("RETURN INVALID", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FrameworkMetadataAPIView(APIView):
    @swagger_auto_schema(response={status.HTTP_200_OK: FrameworkMetadataResponseSerializer})
    def get(self, request, format=None):
        response_data = {
            "references": cached_references,
            "sr_versions": cached_sr_versions,
            "problem_type_data": cached_problem_type_data,
            "wcag_table_info": cached_wcag_table_info,
            "vpat_data": cached_vpat_data,
            "wcag_test_matching": cached_wcag_test_matching,
        }
        response_serializer = FrameworkMetadataResponseSerializer(response_data)
        return Response(response_serializer.data)


class ApplicationInfoAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(responses={status.HTTP_200_OK: ApplicationInfoResponseSerializer})
    def get(self, request, format=None):
        total, used, free = shutil.disk_usage("/")
        disk_usage = "ok"
        if (used / total) > 0.8:
            disk_usage = "warn"
        if (used / total) > 0.9:
            disk_usage = "alert"
        response_data = {"build": settings.APPLICATION_BUILD_REVISION, "disk_usage": disk_usage}
        response_serializer = ApplicationInfoResponseSerializer(response_data)
        return Response(response_serializer.data)


class MetaDataForIssueAPIView(APIView):
    def get(self, request, err_id):
        data = xlsdata.get_data_for_issue(err_id)
        return Response(data)
