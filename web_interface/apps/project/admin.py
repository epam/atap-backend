from django.contrib import admin

from web_interface.apps.project.models import Project, ProjectRole, ProjectPermission

admin.site.register(Project)
admin.site.register(ProjectRole)
admin.site.register(ProjectPermission)
