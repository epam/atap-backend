# Generated by Django 2.2.19 on 2021-12-26 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0003_auto_20210118_1549'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='estimated_testing_time',
            field=models.IntegerField(null=True),
        ),
    ]
