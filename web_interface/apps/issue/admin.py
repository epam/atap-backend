from django.contrib import admin

from web_interface.apps.issue.models import Example, ExampleScreenshot, PageScreenshot


admin.site.register(Example)
admin.site.register(ExampleScreenshot)
admin.site.register(PageScreenshot)
