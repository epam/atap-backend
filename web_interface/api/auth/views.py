import requests

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, mixins
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from axes.models import AccessAttempt

from web_interface.apps.system.parameter_manager import get_parameter
from web_interface.api.auth.serializers import (
    CheckerAPIKeySerializer, AuthTokenResponseSerializer, CheckerAPIKeyResponseSerializer, AuthTokenCaptchaSerializer
)
from web_interface.apps.api_key.models import CheckerAPIKey
from web_interface.apps.task import api_token


class CustomAuthToken(ObtainAuthToken):
    permission_classes = {
        'post': (),
        'delete': (IsAuthenticated,)
    }

    def get_permissions(self):
        return {
            key: [permission() for permission in permissions]
            for key, permissions in self.permission_classes.items()
        }

    def check_permissions(self, request):
        method = request.method.lower()
        for permission in self.get_permissions().get(method, ()):
            if not permission.has_permission(request, self):
                self.permission_denied(
                    request, message=getattr(permission, 'message', None)
                )


    @swagger_auto_schema(request_body=AuthTokenCaptchaSerializer,
                         responses={status.HTTP_200_OK: AuthTokenResponseSerializer,
                                    status.HTTP_400_BAD_REQUEST: AuthTokenCaptchaSerializer,
                                    status.HTTP_401_UNAUTHORIZED: "The login attempts limit has been reached. "
                                                                  "Try again later",
                                    status.HTTP_403_FORBIDDEN: "Blocked by reCAPTCHA"
                                    })
    def post(self, request, *args, **kwargs):
        RECAPTCHA_SECRET_KEY = get_parameter("RECAPTCHA_SECRET_KEY")
        if RECAPTCHA_SECRET_KEY:
            data = {
                'response': request.data.get('token'),
                'secret': RECAPTCHA_SECRET_KEY
            }
            resp = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
            result_json = resp.json()
            if not result_json.get('success'):
                return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})

        access_query = AccessAttempt.objects.filter(username=request.data['username'])
        valid = serializer.is_valid(raise_exception=False)

        if access_query:
            if access_query[0].failures_since_start > 5:
                return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        if not valid:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        response_serializer = AuthTokenResponseSerializer({
            'token': token.key,
            'user_id': user.pk
        })
        return Response(response_serializer.data)

    def delete(self, request, *args, **kwargs):
        try:
            token = Token.objects.get(user=request.user)
        except Token.DoesNotExist:
            pass
        except Token.MultipleObjectsReturned:
            tokens = Token.objects.filter(user=request.user)
            for token in tokens:
                token.delete()
        else:
            token.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckerAPIKeyViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = CheckerAPIKey.objects.order_by('pk')
    serializer_class = CheckerAPIKeySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer) -> tuple:
        return serializer.save(user=self.request.user)

    @swagger_auto_schema(request_body=CheckerAPIKeySerializer,
                         responses={status.HTTP_200_OK: CheckerAPIKeyResponseSerializer,
                                    status.HTTP_400_BAD_REQUEST: CheckerAPIKeySerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _, key = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        response_serializer = CheckerAPIKeyResponseSerializer(
            {'key': key}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(methods=['POST'], detail=False)
    def delete(self, request, *args, **kwargs):
        token_id = request.data.get('token_id')
        if not token_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        api_token.delete_token(token_id, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
