# Generated by Django 2.2.19 on 2021-05-04 04:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issue', '0004_auto_20210304_1035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='example',
            name='number_in_task',
        ),
        migrations.AddField(
            model_name='example',
            name='uuid',
            field=models.CharField(max_length=40, null=True),
        ),
    ]
