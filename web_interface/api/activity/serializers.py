import base64
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers

from web_interface.apps.activity.models import Activity


class ActivityValidationSerializer(serializers.Serializer):
    is_valid = serializers.BooleanField()
    message = serializers.CharField()

    class Meta:
        fields = ('is_valid', 'message')


class ActivitySerializer(serializers.ModelSerializer):
    file = serializers.CharField(required=False)
    filename = serializers.CharField(required=False)

    def to_internal_value(self, data):
        if "file" in data and data["file"] is not None:
            data['side_file'] = base64.b64decode(data['file'].encode('utf=8'))
        return super().to_internal_value(data)

    def to_representation(self, instance):
        result = {
            "id": instance.id,
            "name": instance.name,
            "page": instance.page.id
        }

        if instance.click_sequence is not None:
            result["click_sequence"] = instance.click_sequence

        if instance.side_file:
            result["file"] = base64.b64encode(instance.side_file.read()).decode('utf-8')
            result["filename"] = instance.filename
        return result

    def validate(self, attrs):
        if "file" in attrs and ("filename" not in attrs or attrs['filename'] is None):
            raise serializers.ValidationError("filename missing but file provided")
        return attrs

    def create(self, validated_data):
        data_src = None
        if 'file' in validated_data:
            data_src = base64.b64decode(validated_data.pop('file').encode('utf=8'))
        instance = super().create(validated_data)
        if data_src is not None:
            f = ContentFile(data_src if data_src else '')
            new_file_name = uuid.uuid4().hex
            instance.side_file.save(new_file_name, f)
        return instance

    class Meta:
        model = Activity
        fields = (
            'id',
            'name',
            'click_sequence',
            'file',
            'filename',
            'page'
        )
