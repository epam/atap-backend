from django.contrib import admin

from .models import PlannedTask


class PlannedTaskAdmin(admin.ModelAdmin):
    list_display = ('job', 'next_start_time', 'repeatability', 'start_date', 'end_date', 'creator')


admin.site.register(PlannedTask, PlannedTaskAdmin)
