from django.db import models

from web_interface.apps.page.models import Page


class Activity(models.Model):
    name = models.CharField(max_length=255)
    page = models.ForeignKey(Page, related_name='activities', on_delete=models.CASCADE)
    # Stored as CSV, contains a list of CSS selectors
    click_sequence = models.CharField(max_length=2000, null=True)
    side_file = models.FileField(null=True)
    filename = models.CharField(max_length=500, null=True)

    class Meta:
        db_table = 'activity'
