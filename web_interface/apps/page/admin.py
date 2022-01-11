from django.contrib import admin

from web_interface.apps.page.models import Page


class PageAdmin(admin.ModelAdmin):
    pass
    # list_filter = ('project', )


admin.site.register(Page, PageAdmin)
