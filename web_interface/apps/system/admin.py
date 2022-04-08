from django.contrib import admin

from web_interface.apps.system.models import CheckerParameter


class CheckerParameterAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')


admin.site.register(CheckerParameter, CheckerParameterAdmin)
