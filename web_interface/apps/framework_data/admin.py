from django.contrib import admin

from web_interface.apps.framework_data.models import Test, TestResults, AvailableTest, TestTiming

admin.site.register(Test)
admin.site.register(TestResults)

class AvailableTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'time_data', 'human_name')

class TestTimingAdmin(admin.ModelAdmin):
    list_display = ('name', 'run_times', 'page_size_data', 'timestamp')

admin.site.register(TestTiming, TestTimingAdmin)
admin.site.register(AvailableTest, AvailableTestAdmin)