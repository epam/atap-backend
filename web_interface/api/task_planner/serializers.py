from rest_framework import serializers

from web_interface.apps.task_planner.models import PlannedTask


class PlannedTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = PlannedTask
        fields = (
            'id',
            'name',
            'job',
            'next_start_time',
            'creator',
            'repeatability',
            'start_date',
            'end_date',
            'custom_weekdays',
        )
