from django.db import models


class CheckerParameter(models.Model):
    key = models.CharField(max_length=255)
    value = models.CharField(null=True, blank=True, max_length=1000)

