from django.contrib import admin

from web_interface.apps.task.models import Task, SitemapTask, Report


class TaskAdmin(admin.ModelAdmin):
    list_display = ('target_job', 'date_started', 'last_reported', 'status', 'message', 'progress', 'test_results')


class ReportAdmin(admin.ModelAdmin):
    list_display = ('task', 'delta_starting_task', 'date_created', 'status', 'generated_report')


class SitemapTaskAdmin(admin.ModelAdmin):
    pass
    # list_display = ()


admin.site.register(Task, TaskAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(SitemapTask, SitemapTaskAdmin)
