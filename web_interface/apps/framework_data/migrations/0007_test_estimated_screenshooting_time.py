# Generated by Django 2.2.19 on 2022-01-30 04:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('framework_data', '0006_test_estimated_testing_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='estimated_screenshooting_time',
            field=models.IntegerField(null=True),
        ),
    ]
