from django.db.models import Subquery
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from web_interface.api.report.swagger_serializers import (
    VpatReportParamsWSAGSwaggerSerializer, VpatReportParamsChaptersSwaggerSerializer
)
from web_interface.api.task.serializers import ReportSerializer
from web_interface.apps.framework_data.models import Test, TestResults, AvailableTest
from web_interface.apps.issue.example_manipulation import get_available_problem_types
from web_interface.apps.issue.models import Example
from web_interface.apps.page.models import Page
from web_interface.apps.project.models import Project
from web_interface.apps.report.models import (
    VpatReportParams, ConformanceLevel, Issue, SuccessCriteriaLevel, Section508Chapters, Section508Criteria, IssueLabel
)
from web_interface.api.example.serializers import ExampleScreenshotSerializer
from web_interface.apps.task.models import Task


class SuccessCriteriaLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuccessCriteriaLevel
        fields = '__all__'


class Section508ChaptersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section508Chapters
        fields = '__all__'


class Section508CriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section508Criteria
        fields = '__all__'


class IssueLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueLabel
        fields = '__all__'


class PartialVpatReportParamsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VpatReportParams
        fields = (
            'id',
            'project',
            'type',
            'standart',
            'product_description',
            'notes',
            'evaluation_methods',
            'product_type',
            'date',
            'name',
            'product_name_version',
            'contact',
            'terms',
            'section_508_note',
            'section_en_note',
            'applicable_en',
            'applicable_508',
            'wcag_a_note',
            'wcag_aa_note',
            'wcag_aaa_note'
        )
        extra_kwargs = {
            'notes': {'required': False, 'allow_blank': True}
        }

    def validate_type(self, value):
        """Check is reports available by type for demo user"""
        request = self.context['request']
        if request.user.is_demo_user and request.method.lower() in ('post', 'put', 'patch'):
            available_reports = request.user.demo_permissions.available_reports or ()
            if value not in available_reports:
                raise serializers.ValidationError(
                    'Report with type "{}" is not available for this user. '
                    'Contact your administrator to change your subscription plan.'.format(
                        value
                    )
                )
        return value


class VpatReportParamsSerializer(PartialVpatReportParamsSerializer):
    test_results = serializers.SerializerMethodField()
    wcag = serializers.SerializerMethodField()
    chapters_508 = serializers.SerializerMethodField()
    chapters_EN = serializers.SerializerMethodField()

    class Meta(PartialVpatReportParamsSerializer.Meta):
        fields = PartialVpatReportParamsSerializer.Meta.fields + (
            'job',
            'test_results',
            'wcag',
            'chapters_508',
            'chapters_EN'
        )

    @swagger_serializer_method(
        serializer_or_field=serializers.PrimaryKeyRelatedField(queryset=TestResults.objects.all())
    )
    def get_test_results(self, obj):
        return self.context.get('test_results')

    @swagger_serializer_method(serializer_or_field=VpatReportParamsWSAGSwaggerSerializer)
    def get_wcag(self, obj):
        return self.context.get('wcag')

    @swagger_serializer_method(serializer_or_field=VpatReportParamsChaptersSwaggerSerializer)
    def get_chapters_508(self, obj):
        return self.context.get('chapters_508')

    @swagger_serializer_method(serializer_or_field=VpatReportParamsChaptersSwaggerSerializer)
    def get_chapters_EN(self, obj):
        return self.context.get('chapters_EN')


class AuditReportPagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = (
            'id',
            'name',
            'url'
        )


class ExampleAuditReportSerializer(serializers.ModelSerializer):
    screenshots = serializers.SerializerMethodField()
    pages = AuditReportPagesSerializer(
        many=True, read_only=True, allow_empty=True
    )

    class Meta:
        model = Example
        fields = (
            'id',
            'issue',
            'title',
            'problematic_element_selector',
            'code_snippet',
            'pages',
            'severity',
            'steps',
            'expected_result',
            'actual_result',
            'note',
            'recommendations',
            'screenshots'
        )

    @swagger_serializer_method(serializer_or_field=serializers.ListSerializer(child=serializers.CharField()))
    def get_screenshots(self, obj):
        return ExampleScreenshotSerializer(obj.examplescreenshot_set, many=True).data


class IssuesAuditReportSerializer(serializers.ModelSerializer):
    examples = ExampleAuditReportSerializer(source='examples.all', many=True, read_only=True)

    class Meta:
        model = Issue
        fields = (
            'id',
            'priority',
            'techniques',
            'intro',
            'err_id',
            'example_shows',
            'type_of_disability',
            'references',
            'recommendations',
            'issue_type',
            'name',
            'wcag',
            'is_best_practice',
            'examples',
            'labels'
        )


class ConformanceLevelSerializer(serializers.ModelSerializer):
    issues = serializers.SerializerMethodField()

    def get_issues(self, level):
        qs = Issue.objects.filter(conformance_levels__pk__contains=level.pk, is_best_practice=False)
        return qs.values_list("name", flat=True)

    class Meta:
        model = ConformanceLevel
        fields = (
            'id',
            'WCAG',
            'level',
            'issues',
            'remark'
        )


class AuditReportProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            'id',
            'name',
            'comment',
            'version',
            'contact',
            'company',
            'testers',
            'visual_impairments'
        )


class IssueTypeSerializer(serializers.Serializer):
    err_id = serializers.CharField()
    name = serializers.CharField()
    WCAG = serializers.CharField()
    expected_result = serializers.CharField()
    actual_result = serializers.CharField()
    type_of_disability = serializers.CharField()
    techniques = serializers.CharField()
    recommendations = serializers.CharField()
    labels = serializers.ListField()
    priority = serializers.CharField()
    intro = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AvailableProblemTypesSerializer(serializers.Serializer):
    wcag = IssueTypeSerializer(many=True)
    bp = IssueTypeSerializer(many=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AuditReportSerializer(serializers.ModelSerializer):
    issues = IssuesAuditReportSerializer(
        source='test_results.prefetched_issues', many=True, read_only=True, allow_empty=True
    )
    wcag_checklist = ConformanceLevelSerializer(
        source='test_results.prefetched_conformance_levels', many=True, read_only=True, allow_empty=True
    )
    project = AuditReportProjectSerializer(source='target_job.project', read_only=True)
    warnings = serializers.SerializerMethodField()
    errors = serializers.SerializerMethodField()
    available_problem_types = serializers.SerializerMethodField()
    latest_report = ReportSerializer()

    class Meta:
        model = Task
        fields = (
            'id',
            'test_results',
            'last_reported',
            'issues',
            'project',
            'wcag_checklist',
            'warnings',
            'errors',
            'available_problem_types',
            'latest_report'
        )

    @swagger_serializer_method(serializer_or_field=ExampleAuditReportSerializer(many=True))
    def get_warnings(self, obj):
        example_qs = Example.objects.filter(severity='WARN', issue=None, test_results=obj.test_results)
        serializer = ExampleAuditReportSerializer(example_qs, many=True)
        return serializer.data

    @swagger_serializer_method(serializer_or_field=serializers.ListSerializer(child=serializers.CharField()))
    def get_errors(self, obj):
        if obj.test_results:
            test_qs = obj.test_results.test_set.filter(
                status__in=(Test.ERROR, Test.NOTRUN, Test.READY)
            )
            test_human_names_qs = AvailableTest.objects.filter(
                name__in=Subquery(test_qs.values('name'))
            ).values_list('human_name', flat=True).distinct()
            return list(test_human_names_qs)
        return []

    @swagger_serializer_method(serializer_or_field=AvailableProblemTypesSerializer)
    def get_available_problem_types(self, obj):
        problem_types_wcag, problem_types_bp = get_available_problem_types()
        serializer = AvailableProblemTypesSerializer({
            'wcag': problem_types_wcag,
            'bp': problem_types_bp
        })
        return serializer.data
