import json
from rest_framework import serializers

from web_interface.api.example.serializers import IssueSerializer, ExampleSerializer
from web_interface.api.jira.serializers import JiraWorkerTaskSerializer
from web_interface.api.project.serializers import ExtendedProjectSerializer
from web_interface.apps.framework_data.models import AvailableTest
from web_interface.apps.task.models import Task, SitemapTask, Report


class ReportSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="task.target_job.project.name")
    job_name = serializers.CharField(source="task.target_job.name")
    message = serializers.CharField(source="task.message")
    job_id = serializers.IntegerField(source="task.target_job.id")
    target_task_date_started = serializers.DateTimeField(source="task.date_started")
    project_id = serializers.IntegerField(source="task.target_job.project.id")
    starting_task_date_started = serializers.SerializerMethodField()

    def get_starting_task_date_started(self, obj):
        if obj.delta_starting_task is not None:
            return obj.delta_starting_task.date_started
        else:
            return None

    class Meta:
        model = Report
        fields = (
            'id',
            'project_name',
            'job_name',
            'message',
            'task',
            'delta_starting_task',
            # 'date_started',
            'date_created',
            'status',
            'job_id',
            'project_id',
            'target_task_date_started',
            'starting_task_date_started'
            # 'name'
        )


class TaskSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    jira_worker_task = JiraWorkerTaskSerializer(required=False)
    latest_report = ReportSerializer()

    def get_progress(self, obj):
        return json.loads(obj.progress) if obj.progress is not None else None

    class Meta:
        model = Task
        fields = (
            'id',
            'target_job',
            'date_started',
            'status',
            'message',
            'test_results',
            'last_reported',
            'progress',
            'jira_worker_task',
            'latest_report'
        )


class SitemapTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SitemapTask
        fields = (
            'id',
            'project',
            'status',
            'message'
        )


class TaskReportsSerializer(serializers.ModelSerializer):
    examples = ExampleSerializer(source='test_results.example_set.all', many=True, read_only=True)
    issues = IssueSerializer(source='test_results.issues.all', many=True, read_only=True)
    project = ExtendedProjectSerializer(source='target_job.project', read_only=True)

    class Meta:
        model = Task
        fields = (
            'id',
            'target_job',
            'date_started',
            'status',
            'message',
            'test_results',
            'examples',
            'issues',
            'project'
        )


class AbortTaskSerializer(serializers.Serializer):
    status = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AbortTestForTaskRequestSerializer(serializers.Serializer):
    test_name = serializers.CharField()

    def validate_test_name(self, value):
        return value

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class GenerateReportRequestSerializer(serializers.Serializer):
    delta_starting_task = serializers.IntegerField(required=False)
    is_delta_report = serializers.BooleanField()

    def validate_delta_starting_task(self, value):
        return value

    def validate_is_delta_report(self, value):
        return value

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AbortTestForTaskResponseSerializer(serializers.Serializer):
    status = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ReportDownloadSerializer(serializers.Serializer):
    status = serializers.CharField()
    filename = serializers.CharField()
    report = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class StartJiraIntegrationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class TaskDownloadPieChartSerializer(serializers.Serializer):
    alttext = serializers.CharField()
    image = serializers.CharField()
    filename = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class RunningTasksProgressTasksStatusSerializer(serializers.Serializer):
    overall_progress = serializers.CharField()
    thread_count = serializers.IntegerField(min_value=0, read_only=True)
    thread_status = serializers.JSONField(read_only=True)
    thread_task_cancellable = serializers.JSONField(read_only=True)
    thread_test_name = serializers.JSONField(read_only=True)
    thread_time_started = serializers.JSONField(read_only=True)
    tasks_complete = serializers.IntegerField(min_value=0, read_only=True)
    tasks_count = serializers.IntegerField(min_value=0, read_only=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class RunningTasksTasksStatusSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(min_value=1, read_only=True)
    job_id = serializers.IntegerField(min_value=1, read_only=True)
    project_id = serializers.IntegerField(min_value=1, read_only=True)
    progress = RunningTasksProgressTasksStatusSerializer(read_only=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class QueueDataTasksStatusSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(min_value=1, read_only=True)
    job_id = serializers.IntegerField(min_value=1, read_only=True)
    job_name = serializers.CharField(allow_null=True, allow_blank=True, read_only=True)
    project_id = serializers.IntegerField(min_value=1, read_only=True)
    project_name = serializers.CharField(allow_null=True, allow_blank=True, read_only=True)
    date_started = serializers.DateTimeField(allow_null=True, read_only=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class TasksStatusSerializer(serializers.Serializer):
    running_tasks = RunningTasksTasksStatusSerializer(many=True, read_only=True)
    queue_data = QueueDataTasksStatusSerializer(many=True, read_only=True)
    all_queued_count = serializers.IntegerField(min_value=0)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
