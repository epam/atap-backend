# Generated by Django 2.2.19 on 2021-06-21 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task_planner', '0003_auto_20210621_1131'),
    ]

    operations = [
        migrations.AddField(
            model_name='plannedtask',
            name='start_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
