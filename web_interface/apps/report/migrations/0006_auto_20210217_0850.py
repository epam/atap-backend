# Generated by Django 2.2.5 on 2021-02-17 08:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0005_auto_20210211_1239'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='conformancelevel',
            name='issue_groups',
        ),
        migrations.AlterModelTable(
            name='issue',
            table='issue',
        ),
    ]