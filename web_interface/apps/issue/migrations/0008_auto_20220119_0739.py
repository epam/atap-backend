# Generated by Django 2.2.19 on 2022-01-19 07:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('issue', '0007_examplescreenshot_resolutions'),
    ]

    operations = [
        migrations.RenameField(
            model_name='examplescreenshot',
            old_name='resolutions',
            new_name='resolution',
        ),
    ]