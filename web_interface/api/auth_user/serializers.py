from django.contrib.auth import password_validation
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from web_interface.apps.auth_user.models import DemoPermissions, AuthUser
from web_interface.apps.framework_data.models import AvailableTest


class DemoPermissionsSerializer(serializers.ModelSerializer):
    available_tests = serializers.SerializerMethodField()

    class Meta:
        model = DemoPermissions
        fields = (
            'projects_quota',
            'pages_quota',
            'jobs_quota',
            'running_jobs_quota',

            'current_projects_count',
            'current_jobs_count',
            'current_running_jobs_count',

            'available_tests',
            'available_reports',
            'is_reports_readonly',
            'created_stamp',
            'updated_stamp'
        )

    @swagger_serializer_method(serializer_or_field=serializers.ListSerializer(child=serializers.CharField()))
    def get_available_tests(self, obj):
        available_tests = obj.available_tests
        axe_tests = AvailableTest.objects.exclude(name__startswith='test_').values_list('name', flat=True)
        available_tests.extend(axe_tests)
        return set(available_tests)


class AuthUserSerializer(serializers.ModelSerializer):
    demo_permissions = DemoPermissionsSerializer()

    class Meta:
        model = AuthUser
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'is_active',
            'is_superuser',
            'change_password',
            'email',
            'demo_permissions',
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(min_length=8, max_length=32, write_only=True, required=True)
    new_password = serializers.CharField(min_length=8, max_length=32, write_only=True, required=True)
    new_password_confirmation = serializers.CharField(min_length=8, max_length=32, write_only=True, required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
             'You have entered an invalid old password. Please try again.'
            )
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirmation']:
            raise serializers.ValidationError({'new_password_confirmation': 'The two password fields did not match.'})
        password_validation.validate_password(data['new_password'], self.context['request'].user)
        return data

    def save(self, **kwargs):
        password = self.validated_data['new_password']
        user = self.context['request'].user
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
