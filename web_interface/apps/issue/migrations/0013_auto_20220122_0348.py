# Generated by Django 2.2.19 on 2022-01-22 03:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('issue', '0012_examplescreenshot_resolution'),
    ]

    operations = [
        migrations.RenameField(
            model_name='example',
            old_name='resolution',
            new_name='affected_resolutions',
        ),
        migrations.RemoveField(
            model_name='examplescreenshot',
            name='resolution',
        ),
    ]
