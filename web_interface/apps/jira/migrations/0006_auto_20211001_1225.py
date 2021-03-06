# Generated by Django 2.2.19 on 2021-10-01 12:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jira', '0005_auto_20211001_0802'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jiraworkertask',
            name='task',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='jira_worker_task', to='task.Task'),
        ),
        migrations.AlterModelTable(
            name='jiraworkertask',
            table='jira_worker_task',
        ),
    ]
