# Generated by Django 2.2.5 on 2021-02-01 09:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0003_auto_20210118_1425'),
    ]

    operations = [
        migrations.RenameField(
            model_name='conformancelevel',
            old_name='issue_group',
            new_name='issue_groups',
        ),
    ]
