from django.core.files.base import ContentFile
from rest_framework import serializers

from web_interface.apps.issue.models import Example, ExampleScreenshot
from web_interface.apps.page.models import Page
from web_interface.apps.report.models import Issue
import base64
import uuid


class IssueSerializer(serializers.ModelSerializer):
    examples = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = (
            'id',
            'err_id',
            'test_results',
            'examples',
            'priority',
            'techniques',
            'intro',
            'example_shows',
            'type_of_disability',
            'references',
            'recommendations',
            'name',
            'issue_type',
            'wcag',
            'is_best_practice',
            'labels'
        )


class ExampleSerializer(serializers.ModelSerializer):
    pages = serializers.ManyRelatedField(
        allow_empty=True, required=False,
        child_relation=serializers.PrimaryKeyRelatedField(allow_empty=False, queryset=Page.objects.all())
    )

    class Meta:
        model = Example
        fields = (
            'id',
            'test_results',
            'err_id',
            'test',
            'problematic_element_selector',
            'code_snippet',
            'pages',
            'severity',
            'steps',
            'actual_result',
            'note',
            'expected_result',
            'issue',
            'uuid',
            'force_best_practice',
            'order_in_issuegroup',
            'recommendations'
        )


class ExampleScreenshotSerializer(serializers.ModelSerializer):
    image = serializers.CharField()

    def to_internal_value(self, data):
        data = data.copy()
        data['screenshot'] = base64.b64decode(data['image'].encode('utf=8'))
        return super(ExampleScreenshotSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        return {
            "id": instance.id,
            "example": instance.example.id,
            "image": base64.b64encode(instance.screenshot.read()).decode('utf-8')
        }

    def update(self, instance, validated_data):
        data_src = validated_data.pop('image')
        super(ExampleScreenshotSerializer, self).update(instance, validated_data)
        f = ContentFile(base64.b64decode(data_src.encode('utf-8')) if data_src else '')
        new_file_name = uuid.uuid4().hex
        instance.screenshot.save(new_file_name, f)
        return instance

    def create(self, validated_data):
        data_src = validated_data.pop('image')
        instance = super(ExampleScreenshotSerializer, self).create(validated_data)
        f = ContentFile(base64.b64decode(data_src.encode('utf-8')) if data_src else '')
        new_file_name = uuid.uuid4().hex
        instance.screenshot.save(new_file_name, f)
        return instance

    class Meta:
        model = ExampleScreenshot
        fields = ['example', 'image', 'id']


class IssueForWarnSerializer(serializers.Serializer):
    is_best_practice = serializers.BooleanField(required=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class IssuePrioritiesSerializer(serializers.ListSerializer):
    child = serializers.CharField()

    def update(self, instance, validated_data):
        pass


class IssueLabelsSerializer(serializers.ListSerializer):
    child = serializers.CharField()

    def update(self, instance, validated_data):
        pass
