from django.db import models
from django.conf import settings

from web_interface.apps.job.models import Job


class PlannedTask(models.Model):
    RUN_ONCE = 'run_once'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    MONTHLY_DATE = 'monthly_date'
    MONTHLY_WEEK_DAY = 'monthly_week_day'
    MONTHLY_LAST_WEEK_DAY = 'monthly_last_week_day'
    ON_WEEK_DAYS = 'on_week_days'

    REPEATABILITY_CHOICES = (
        (RUN_ONCE, 'RUN_ONCE'),
        (DAILY, 'DAILY'),
        (WEEKLY, 'WEEKLY'),
        (MONTHLY, 'MONTHLY'),
        (MONTHLY_DATE, 'MONTHLY_DATE'),
        (MONTHLY_WEEK_DAY, 'MONTHLY_WEEK_DAY'),
        (MONTHLY_LAST_WEEK_DAY, 'MONTHLY_LAST_WEEK_DAY'),
        (ON_WEEK_DAYS, 'ON_WEEK_DAYS')
    )

    job = models.ForeignKey(Job, related_name='planned_task', on_delete=models.CASCADE)
    name = models.CharField(max_length=300, null=False, blank=False)
    next_start_time = models.DateTimeField(null=False, blank=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    repeatability = models.CharField(max_length=40, choices=REPEATABILITY_CHOICES, blank=True)
    start_date = models.DateTimeField(null=False, blank=False)
    end_date = models.DateTimeField(blank=True, null=True)
    custom_weekdays = models.CharField(max_length=300, null=True, blank=True)

    class Meta:
        db_table = 'planned_task'
