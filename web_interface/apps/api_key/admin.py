from django.contrib import admin
from rest_framework_api_key.admin import APIKeyModelAdmin
from .models import CheckerAPIKey


@admin.register(CheckerAPIKey)
class OrganizationAPIKeyModelAdmin(APIKeyModelAdmin):
    pass
