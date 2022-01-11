from django.contrib import admin

from .models import JiraIntegrationParams, JiraWorkerTask


class JiraIntegrationParamsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'project',
        'host',
        'username',
        'token',
        'jira_project_key',
    )


class JiraWorkerTaskAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'status',
        'task',
        'message',
        'total_examples',
        'processed_examples'
    )


admin.site.register(JiraIntegrationParams, JiraIntegrationParamsAdmin)
admin.site.register(JiraWorkerTask, JiraWorkerTaskAdmin)
