# Generated by Django 2.2.19 on 2021-09-22 10:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issue', '0005_auto_20210504_0458'),
    ]

    operations = [
        migrations.AddField(
            model_name='example',
            name='problematic_element_position',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
    ]
