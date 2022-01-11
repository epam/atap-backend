from rest_framework import serializers


class UrlValidationSerializer(serializers.Serializer):
    url = serializers.URLField(required=True, allow_blank=False)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class UrlValidationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    is_valid = serializers.BooleanField()
    title = serializers.CharField(required=False)
    status_code = serializers.IntegerField(required=False)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AuthSettingSerializer(serializers.Serializer):
    activator = serializers.CharField(allow_blank=True)
    login = serializers.CharField(allow_blank=True)
    password = serializers.CharField(allow_blank=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AuthValidationSerializer(serializers.Serializer):
    url = serializers.URLField(required=True, allow_blank=False)
    auth_type = serializers.CharField()
    auth_setting = AuthSettingSerializer()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AuthValidationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    is_valid = serializers.BooleanField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class FrameworkMetadataResponseSerializer(serializers.Serializer):
    references = serializers.ListField()
    sr_versions = serializers.ListField()
    problem_type_data = serializers.JSONField()
    wcag_table_info = serializers.JSONField()
    vpat_data = serializers.JSONField()
    wcag_test_matching = serializers.JSONField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ApplicationInfoResponseSerializer(serializers.Serializer):
    build = serializers.CharField()
    disk_usage = serializers.ChoiceField(choices=["ok", "warn", "alert"])

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
