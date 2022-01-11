from django.conf import settings
from django.db import models
from rest_framework_api_key.models import AbstractAPIKey

from web_interface.apps.project.models import Project


class CheckerAPIKey(AbstractAPIKey):
    project = models.ForeignKey(Project, related_name='api_keys', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = 'checker_api_key'
