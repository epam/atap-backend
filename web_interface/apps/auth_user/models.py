from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres import fields as pg_fields
from django.db import models


class AuthUser(AbstractUser):
    change_password = models.BooleanField(blank=True, null=True, default=True)

    class Meta:
        db_table = 'auth_user'

    @property
    def is_demo_user(self) -> bool:
        return hasattr(self, 'demo_permissions')


class DemoPermissions(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='demo_permissions'
    )

    projects_quota = models.PositiveIntegerField(default=1)
    pages_quota = models.PositiveIntegerField(default=3)
    jobs_quota = models.PositiveIntegerField(default=10)
    running_jobs_quota = models.PositiveIntegerField(default=2)

    available_tests = pg_fields.ArrayField(models.CharField(max_length=255), null=True)
    available_reports = pg_fields.ArrayField(models.CharField(max_length=255), null=True)

    is_reports_readonly = models.BooleanField(default=True)

    created_stamp = models.DateTimeField(auto_now_add=True)
    updated_stamp = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'demo_permissions'

    @property
    def hardcoded_available_reports(self) -> list:
        return [
            'INT',
            '508',
            'EN',
            'WCAG'
        ]

    @property
    def hardcoded_available_tests(self) -> list:
        """
        Group of the most stable and fastest tests (the suite of these tests should be customizable).
        Filters displayed to the user are also customizable. By default only ALL (set None to field)
        """
        return [
            'test_title',
            'test_image_alt',
            'test_text_contrast',
            'test_tables_struct',
            'test_h51',
            'test_empty_link',
            'test_img_link',
            'test_link_without_href',
            'test_links_with_same_resource',
            'test_svg_icon_link',
            'test_related_elements_as_list',
            'test_visible_list',
            'test_markup'
        ]

    def current_projects_count(self) -> int:
        from web_interface.apps.project.models import Project
        projects_created_count = Project.objects.filter(users=self.user).count()
        return projects_created_count

    def current_jobs_count(self) -> int:
        from web_interface.apps.job.models import Job
        jobs_created = Job.objects.filter(project__users=self.user).count()
        return jobs_created

    def current_running_jobs_count(self) -> int:
        from web_interface.apps.job.models import Job
        from web_interface.apps.task.models import Task
        running_jobs = Job.objects.filter(
            project__users=self.user,  task__status__in=(Task.QUEUED, Task.RUNNING)
        ).count()
        return running_jobs
