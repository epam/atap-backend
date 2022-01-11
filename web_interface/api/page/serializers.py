from rest_framework import serializers

from web_interface.apps.page.models import Page
from web_interface.api.activity.serializers import ActivitySerializer


class PageSerializer(serializers.ModelSerializer):
    activities = ActivitySerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = (
            'id',
            'name',
            'url',
            'activities',
            'project',
            'parent_page'
        )
