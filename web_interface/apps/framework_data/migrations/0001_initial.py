# Generated by Django 2.2.5 on 2020-11-30 11:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AvailableTest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('human_name', models.CharField(max_length=300)),
            ],
            options={
                'db_table': 'available_test',
            },
        ),
        migrations.CreateModel(
            name='TestResults',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'test_results',
            },
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=1000)),
                ('status', models.CharField(max_length=20)),
                ('support_status', models.CharField(max_length=20)),
                ('checked_elements', models.TextField(null=True)),
                ('problematic_pages', models.TextField()),
                ('manually', models.BooleanField(default=False)),
                ('test_results', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='framework_data.TestResults')),
            ],
            options={
                'db_table': 'test',
            },
        ),
    ]