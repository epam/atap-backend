# Generated by Django 2.2.5 on 2020-12-20 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('framework_data', '0002_availabletest_time_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestTiming',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=1000)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('page_size_data', models.CharField(max_length=10000, null=True)),
                ('run_times', models.IntegerField(default=1)),
            ],
        ),
    ]