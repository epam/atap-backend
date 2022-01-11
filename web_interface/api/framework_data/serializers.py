from typing import List

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from framework.libs.basic_groups import BASED_TEST_HARDCODE
from web_interface.apps.framework_data.models import TestResults, AvailableTest, AvailableTestGroup


class TestResultSerializer(serializers.ModelSerializer):
    issues = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = TestResults
        fields = ("id", "issues")


class AvailableTestGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableTestGroup
        fields = ("id", "name")


class AvailableTestSerializer(serializers.ModelSerializer):
    groups_names = serializers.SerializerMethodField()
    major = serializers.SerializerMethodField()
    axe = serializers.SerializerMethodField()
    # basic_1 = serializers.SerializerMethodField()
    # basic_2 = serializers.SerializerMethodField()
    # average_time = serializers.SerializerMethodField()

    class Meta:
        model = AvailableTest
        fields = (
            "id",
            "name",
            "human_name",
            "groups",
            "groups_names",
            "major",
            "axe"
            # 'basic_1',
            # 'basic_2',
            # 'average_time'
        )

    @swagger_serializer_method(serializer_or_field=serializers.ListSerializer(child=serializers.CharField()))
    def get_groups_names(self, obj: AvailableTest) -> List[str]:
        return obj.groups.values_list("name", flat=True)

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_major(self, obj: AvailableTest) -> bool:
        if obj.name in BASED_TEST_HARDCODE:
            return True
        return False

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_axe(self, obj: AvailableTest) -> bool:
        if not obj.name.startswith("test_"):
            return True
        return False

    # @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    # def get_basic_1(self, obj: AvailableTest) -> bool:
    #     if obj.name in HARDCODE_TESTS_BASIC_1:
    #         return True
    #     return False

    # @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    # def get_basic_2(self, obj: AvailableTest) -> bool:
    #     if obj.name in HARDCODE_TESTS_BASIC_2:
    #         return True
    #     return False

    # @swagger_serializer_method(serializer_or_field=serializers.CharField)
    # def get_average_time(self, obj: AvailableTest) -> str:
    #     import json
    #     with open(r'framework/time_of_tests/average_time.json', 'r', encoding='utf-8') as f:
    #         time_data = json.load(f)
    #     try:
    #         return time_data[obj.name]
    #     except KeyError:
    #         return 'None'


class TestTimingSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=1000)
    date_was_run_y_m_d = serializers.CharField()
    page_load_time = serializers.FloatField()
    all_elements_count = serializers.IntegerField()
    a = serializers.IntegerField()
    img = serializers.IntegerField()
    button = serializers.IntegerField()
    input = serializers.IntegerField()
    form = serializers.IntegerField()
    table = serializers.IntegerField()
    div = serializers.IntegerField()
    span = serializers.IntegerField()
