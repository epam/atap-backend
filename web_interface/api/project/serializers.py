from django.db import IntegrityError, transaction
from rest_framework import serializers

from web_interface.api.jira.serializers import JiraIntegrationParamsSerializer
from web_interface.apps.jira.models import JiraIntegrationParams
from web_interface.apps.project.models import Project, ProjectPermission, ProjectRole


class ProjectPermissionSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.name', max_length=255)

    class Meta:
        model = ProjectPermission
        fields = (
            'user',
            'role'
        )


class SimplifiedProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            'id',
            'name'
        )


class ExtendedProjectSerializer(serializers.ModelSerializer):
    options = serializers.CharField()
    users = ProjectPermissionSerializer(source='project_permissions', many=True, required=False)
    pages = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    jobs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    has_activities = serializers.BooleanField(read_only=True)
    jira_integration_params = JiraIntegrationParamsSerializer(required=False)

    class Meta:
        model = Project
        fields = (
            'id',
            'name',
            'comment',
            'options',
            'version',
            'contact',
            'company',
            'testers',
            'visual_impairments',
            'url',
            'audit_report',
            'vpat_report',
            'test_list',
            'last_test',
            'page_after_login',
            'request_interval',
            'enable_content_blocking',
            'enable_popup_detection',
            'disable_parallel_testing',
            'users',
            'pages',
            'jobs',
            'disclaimer',
            'created_stamp',
            'has_activities',
            'jira_integration_params'
        )
        extra_kwargs = {
            'contact': {'required': False, 'allow_blank': True}
        }

    def validate(self, attrs):
        """Check project quota for demo user"""
        request = self.context['request']
        if request.user.is_demo_user and request.method.lower() == 'post':
            projects_created_count = Project.objects.filter(users=request.user).count()
            if projects_created_count >= request.user.demo_permissions.projects_quota:
                raise serializers.ValidationError(
                    'The quota for creating projects has been exceeded. '
                    'Contact your administrator to change your subscription plan.'
                )
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        users_data = validated_data.pop('project_permissions', [])
        instance = super().create(validated_data)
        users_data.append(
            {
                'user': request.user,
                'role': {'name': 'Creator'}
            }
        )
        for user_data in users_data:
            project_role_data = user_data.pop('role')
            project_role, _ = ProjectRole.objects.get_or_create(**project_role_data)
            try:
                with transaction.atomic():
                    ProjectPermission.objects.create(project=instance, role=project_role, **user_data)
            except IntegrityError as _:
                pass
        return instance

    def update(self, instance, validated_data):
        request = self.context['request']
        users_data = validated_data.pop('project_permissions', [])

        instance.name = validated_data.get('name', instance.name)
        # Stored as CSV, contains a list of tests/test categories to run
        instance.comment = validated_data.get('comment', instance.comment)
        instance.name = validated_data.get('name', instance.name)
        # ?TODO refactor 'options' field to json field
        instance.options = validated_data.get('options', instance.options)
        instance.version = validated_data.get('version', instance.version)
        instance.contact = validated_data.get('contact', instance.contact)
        instance.company = validated_data.get('company', instance.company)
        instance.testers = validated_data.get('testers', instance.testers)
        instance.visual_impairments = validated_data.get('visual_impairments', instance.visual_impairments)
        instance.url = validated_data.get('url', instance.url)
        instance.audit_report = validated_data.get('audit_report', instance.audit_report)
        instance.vpat_report = validated_data.get('vpat_report', instance.vpat_report)
        instance.test_list = validated_data.get('test_list', instance.test_list)
        instance.last_test = validated_data.get('last_test', instance.last_test)
        instance.request_interval = validated_data.get('request_interval', instance.request_interval)
        instance.page_after_login = validated_data.get('page_after_login', instance.page_after_login)
        instance.enable_content_blocking = validated_data.get('enable_content_blocking',
                                                              instance.enable_content_blocking)
        instance.enable_popup_detection = validated_data.get('enable_popup_detection', instance.enable_popup_detection)
        instance.disable_parallel_testing = validated_data.get('disable_parallel_testing',
                                                               instance.disable_parallel_testing)
        instance.save()

        jira_data = None
        if "jira_integration_params" in validated_data:
            jira_data = validated_data.pop("jira_integration_params")

        if jira_data is None:
            if hasattr(instance, "jira_integration_params"):
                instance.jira_integration_params.delete()
        else:
            if hasattr(instance, "jira_integration_params"):
                instance.jira_integration_params.host = jira_data.get("host", instance.jira_integration_params.host)
                instance.jira_integration_params.username = jira_data.get("username",
                                                                          instance.jira_integration_params.username)
                instance.jira_integration_params.token = jira_data.get("token", instance.jira_integration_params.token)
                instance.jira_integration_params.jira_project_key = jira_data.get("jira_project_key",
                                                                                  instance.jira_integration_params.jira_project_key)
                instance.jira_integration_params.save()
            else:
                JiraIntegrationParams.objects.create(project=instance, **jira_data)

        if request.method.lower() == 'patch' and 'project_permissions' not in validated_data:
            return instance
        ProjectPermission.objects.filter(project=instance).delete()
        users_data.append(
            {
                'user': request.user,
                'role': {'name': 'Creator'}
            }
        )
        for user_data in users_data:
            project_role_data = user_data.pop('role')
            project_role, _ = ProjectRole.objects.get_or_create(**project_role_data)
            try:
                with transaction.atomic():
                    ProjectPermission.objects.create(project=instance, role=project_role, **user_data)
            except IntegrityError as _:
                pass
        return instance


class GenerateSitemapSerializer(serializers.Serializer):
    depth_level = serializers.IntegerField(min_value=1, max_value=5, required=False, default=1)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class GenerateSitemapResponseSerializer(serializers.Serializer):
    status = serializers.CharField(required=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class IsSitemapRunningSerializer(serializers.Serializer):
    is_running = serializers.BooleanField(required=True)
 
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class SitemapQuotaInfoSerializer(serializers.Serializer):
    can_start_sitemap = serializers.BooleanField(required=True)
    queue_slots_available = serializers.IntegerField(required=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ProjectCompaniesSerializer(serializers.Serializer):
    companies = serializers.ListSerializer(child=serializers.CharField())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
