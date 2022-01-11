from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer

from web_interface.apps.api_key.models import CheckerAPIKey


class CheckerAPIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckerAPIKey
        fields = (
            'id',
            'name',
            'project',
            'user',
            'prefix',
            'created'
        )
        extra_kwargs = {
            'id': {'read_only': True},
            'user': {'read_only': True},
            'prefix': {'read_only': True},
            'created': {'read_only': True}
        }

    def save(self, **kwargs) -> tuple:
        validated_data = dict(
            list(self.validated_data.items()) + list(kwargs.items())
        )
        return CheckerAPIKey.objects.create_key(**validated_data)


class AuthTokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user_id = serializers.IntegerField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class CheckerAPIKeyResponseSerializer(serializers.Serializer):
    key = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AuthTokenCaptchaSerializer(AuthTokenSerializer):
    token = serializers.CharField(label=("token"))
