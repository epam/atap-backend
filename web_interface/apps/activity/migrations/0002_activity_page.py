# Generated by Django 2.2.5 on 2020-11-30 11:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('page', '0001_initial'),
        ('activity', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='page.Page'),
        ),
    ]
