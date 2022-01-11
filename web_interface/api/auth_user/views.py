from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import get_object_or_404, GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from web_interface.api.auth.serializers import AuthTokenResponseSerializer
from web_interface.api.auth_user.serializers import AuthUserSerializer, ChangePasswordSerializer
from web_interface.apps.auth_user.models import AuthUser


class AuthUserAPIView(APIView):

    @swagger_auto_schema(responses={status.HTTP_200_OK: AuthUserSerializer})
    def get(self, request, format=None):
        queryset = AuthUser.objects.order_by('pk')
        filter_kwargs = {'id': self.request.user.id}
        obj = get_object_or_404(queryset, **filter_kwargs)
        serializer = AuthUserSerializer(obj)
        return Response(serializer.data)


class ChangePasswordAPIView(GenericAPIView):
    serializer_class = ChangePasswordSerializer

    @swagger_auto_schema(request_body=ChangePasswordSerializer,
                         responses={status.HTTP_200_OK: AuthTokenResponseSerializer,
                                    status.HTTP_400_BAD_REQUEST: ChangePasswordSerializer})
    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if hasattr(user, 'auth_token'):
            user.auth_token.delete()
        token, created = Token.objects.get_or_create(user=user)

        response_serializer = AuthTokenResponseSerializer({
            'token': token.key,
            'user_id': user.pk
        })
        return Response(response_serializer.data, status=status.HTTP_200_OK)
