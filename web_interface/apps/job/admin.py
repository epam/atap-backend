from django.contrib import admin

from web_interface.apps.job.models import Job


class JobAdmin(admin.ModelAdmin):
    pass
    # list_filter = ('project', )


admin.site.register(Job, JobAdmin)
