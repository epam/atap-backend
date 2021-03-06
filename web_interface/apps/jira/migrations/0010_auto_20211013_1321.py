# Generated by Django 2.2.19 on 2021-10-13 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jira', '0009_jiraworkertask_issues_reopened'),
    ]

    operations = [
        migrations.RenameField(
            model_name='jiraworkertask',
            old_name='issues_reopened',
            new_name='reopened_issues',
        ),
        migrations.AddField(
            model_name='jiraworkertask',
            name='duplicate_issues',
            field=models.IntegerField(default=0),
        ),
    ]
