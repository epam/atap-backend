from django.db import models

from web_interface.apps.project.models import Project


class Page(models.Model):
    name = models.CharField(max_length=1000)
    url = models.URLField(max_length=1000)
    project = models.ForeignKey(Project, related_name='pages', on_delete=models.CASCADE)
    parent_page = models.ForeignKey('page.Page', on_delete=models.CASCADE, null=True)
    page_size_data = models.CharField(max_length=300, null=True)

    class Meta:
        db_table = 'page'
