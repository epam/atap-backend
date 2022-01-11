from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from web_interface.apps.auth_user.models import AuthUser, DemoPermissions


class DemoPermissionsInline(admin.TabularInline):
    model = DemoPermissions


class AuthUserAdmin(UserAdmin):
    inlines = (
        DemoPermissionsInline,
    )


admin.site.register(AuthUser, AuthUserAdmin)
