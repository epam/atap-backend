from rest_framework import serializers


class VpatReportParamsWSAGLevelsSwaggerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    criteria = serializers.CharField()
    level = serializers.CharField()
    product_type = serializers.CharField(allow_blank=True, allow_null=True)
    remark = serializers.CharField(allow_blank=True, allow_null=True)
    support_level = serializers.CharField(allow_null=True)
    test_results_id = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class VpatReportParamsWSAGNestedSwaggerSerializer(serializers.Serializer):
    number = serializers.CharField()
    title = serializers.CharField()
    levels = serializers.ListSerializer(child=VpatReportParamsWSAGLevelsSwaggerSerializer())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class VpatReportParamsWSAGSwaggerSerializer(serializers.Serializer):
    A = serializers.ListSerializer(child=VpatReportParamsWSAGNestedSwaggerSerializer())
    AA = serializers.ListSerializer(child=VpatReportParamsWSAGNestedSwaggerSerializer())
    AAA = serializers.ListSerializer(child=VpatReportParamsWSAGNestedSwaggerSerializer())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class VpatReportParamsChaptersLevelsSwaggerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    chapter_id = serializers.IntegerField()
    criteria = serializers.CharField()
    level = serializers.CharField()
    product_type = serializers.CharField(allow_blank=True, allow_null=True)
    remark = serializers.CharField(allow_blank=True, allow_null=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class VpatReportParamsChaptersNestedSwaggerSerializer(serializers.Serializer):
    criteria = serializers.CharField()
    levels = serializers.ListSerializer(child=VpatReportParamsChaptersLevelsSwaggerSerializer())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class VpatReportParamsChaptersSwaggerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    note = serializers.CharField(allow_blank=True, allow_null=True)
    number = serializers.CharField()
    title = serializers.CharField()
    criteria = serializers.ListSerializer(child=VpatReportParamsChaptersNestedSwaggerSerializer())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
