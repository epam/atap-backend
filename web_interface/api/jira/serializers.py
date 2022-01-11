from rest_framework import serializers

from web_interface.apps.jira.models import JiraIntegrationParams, JiraWorkerTask


class JiraIntegrationParamsSerializer(serializers.ModelSerializer):

    class Meta:
        model = JiraIntegrationParams
        fields = (
            'host',
            'username',
            'token',
            'jira_project_key',
        )


class JiraValidationSerializer(serializers.Serializer):
    host = serializers.CharField(required=True, allow_blank=False)
    username = serializers.CharField(required=True, allow_blank=False)
    token = serializers.CharField(required=True, allow_blank=False)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class JiraWorkerTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = JiraWorkerTask
        fields = (
            'id',
            'status',
            'message',
            'total_examples',
            'processed_examples',
            'task',
            'total_issues',
            'reopened_issues',
            'duplicated_issues',
        )


class JiraValidationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    is_valid = serializers.BooleanField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
