# Generated by Django 2.2.19 on 2021-09-29 09:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('issue', '0005_auto_20210504_0458'),
        ('jira', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='JiraTask',
            new_name='JiraRootIssue',
        ),
        migrations.AlterModelTable(
            name='jirarootissue',
            table='jira_root_issue',
        ),
    ]
