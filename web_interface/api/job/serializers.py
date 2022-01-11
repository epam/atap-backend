import json

from rest_framework import serializers

from web_interface.api.jira.serializers import JiraWorkerTaskSerializer
from web_interface.api.report.serializers import PartialVpatReportParamsSerializer
from web_interface.apps.job.models import Job
from web_interface.apps.page.models import Page
from web_interface.apps.report.models import VpatReportParams
from web_interface.apps.task import tasks
from web_interface.apps.task.models import Task


class PartialTaskSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    jira_worker_task = JiraWorkerTaskSerializer(required=False)

    def get_progress(self, obj):
        return json.loads(obj.progress) if obj.progress is not None else None

    class Meta:
        model = Task
        fields = (
            'id',
            'date_started',
            'celery_task_id',
            'is_valid',
            'status',
            'message',
            'progress',
            'test_results',
            'last_reported',
            'jira_worker_task'
        )



class SimplifiedJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = (
            'id',
            'name'
        )

class JobTaskSerializer(PartialTaskSerializer):
    class Meta(PartialTaskSerializer.Meta):
        fields = PartialTaskSerializer.Meta.fields + (
            'target_job',
        )


class JobSerializer(serializers.ModelSerializer):
    pages = serializers.PrimaryKeyRelatedField(queryset=Page.objects.all(), many=True, required=False)
    vpat_reports_params = PartialVpatReportParamsSerializer(source='vpatreportparams_set', many=True, required=False)
    last_task = PartialTaskSerializer(source='get_last_task', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    has_jira_integration_params = serializers.SerializerMethodField()

    def get_has_jira_integration_params(self, job) -> bool:
        return hasattr(job.project, "jira_integration_params")

    class Meta:
        model = Job
        fields = (
            'id',
            'name',
            'project',
            'project_name',
            'date_created',
            'last_test',
            'pages',
            'test_list',
            'estimated_testing_time',
            'status',
            'last_task',
            'vpat_reports_params',
            'has_jira_integration_params'
        )

    def validate_pages(self, attrs):
        """Check pages quota for demo user"""
        request = self.context['request']
        if request.user.is_demo_user and request.method.lower() in ('post', 'put', 'patch'):
            pages_count = len(attrs)
            if pages_count > request.user.demo_permissions.pages_quota:
                raise serializers.ValidationError(
                    'The quota for creating pages has been exceeded. '
                    'Contact your administrator to change your subscription plan.'
                )
        return attrs

    def validate_test_list(self, value):
        """Check is tests available for demo user"""
        request = self.context['request']
        test_list = value.split(',')
        test_set = set(filter(lambda test: test.startswith('test_'), test_list))
        if request.user.is_demo_user and request.method.lower() in ('post', 'put', 'patch'):
            available_tests_set = set(request.user.demo_permissions.available_tests or ())
            extra_tests_set = test_set - available_tests_set
            if extra_tests_set:
                raise serializers.ValidationError(
                    'Selected tests ({}) are not available for this user. '
                    'Contact your administrator to change your subscription plan.'.format(
                        ', '.join(extra_tests_set)
                    )
                )
        return value

    def validate(self, attrs):
        """Check jobs_quota and running_jobs_quota for demo user"""
        request = self.context['request']
        if request.user.is_demo_user and request.method.lower() == 'post':
            jobs_created_count = Job.objects.filter(project__users=request.user).count()
            if jobs_created_count >= request.user.demo_permissions.jobs_quota:
                raise serializers.ValidationError(
                    'The quota for creating jobs has been exceeded. '
                    'Contact your administrator to change your subscription plan.'
                )
        return attrs

    def create(self, validated_data):
        vpat_reports_params_data = validated_data.pop('vpatreportparams_set', ())
        instance = super().create(validated_data)

        for vpat_report_params_data in vpat_reports_params_data:
            vpat_report_params_data['project'] = instance.project
            VpatReportParams.objects.create(job=instance, **vpat_report_params_data)

        tasks.update_job_length.apply(kwargs={'job_id': instance.id})
        instance.refresh_from_db()  # important step after celery task
        return instance

    def update(self, instance, validated_data):
        vpat_reports_params_data = validated_data.pop('vpatreportparams_set', ())
        instance = super().update(instance, validated_data)

        VpatReportParams.objects.filter(job=instance).delete()
        for vpat_report_params_data in vpat_reports_params_data:
            vpat_report_params_data['project'] = instance.project
            VpatReportParams.objects.create(job=instance, **vpat_report_params_data)

        tasks.update_job_length.apply(kwargs={'job_id': instance.id})
        instance.refresh_from_db()  # important step after celery task
        return instance


class PrecalculateJobRequestSerializer(serializers.Serializer):
    tests = serializers.ListField()
    pages = serializers.ListField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class PrecalculateJobResponseSerializer(serializers.Serializer):
    time = serializers.IntegerField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
