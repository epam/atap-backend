# Generated by Django 2.2.19 on 2022-01-30 07:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('page', '0004_remove_page_page_after_login'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='estimated_locating_time',
            field=models.IntegerField(null=True),
        ),
    ]
