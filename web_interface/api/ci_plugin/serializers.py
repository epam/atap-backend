from rest_framework import serializers

from web_interface.apps.framework_data.models import Test
from web_interface.apps.job.models import Job
from web_interface.apps.task.models import Task


class CIPluginJobSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Job
        fields = (
            'id',
            'name',
            'project',
            'project_name',
            'date_created'
        )


class CIPluginJobTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = (
            'id',
            'celery_task_id'
        )


class CIPluginTestSerializer(serializers.ModelSerializer):

    class Meta:
        model = Test
        fields = (
            'name',
            'status'
        )


class CIPluginTaskSerializer(serializers.ModelSerializer):
    tests = CIPluginTestSerializer(source='test_results.test_set', many=True, read_only=True)

    class Meta:
        model = Task
        fields = (
            'id',
            'date_started',
            'celery_task_id',
            'is_valid',
            'status',
            'message',
            'tests'
        )


class CIPluginAbortTaskTaskSerializer(serializers.Serializer):
    status = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
