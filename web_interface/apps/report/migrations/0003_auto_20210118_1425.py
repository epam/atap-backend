# Generated by Django 2.2.5 on 2021-01-18 14:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('framework_data', '0003_testtiming'),
        ('report', '0002_auto_20210113_1223'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='conformancelevel',
            unique_together={('WCAG', 'test_results')},
        ),
        migrations.RemoveField(
            model_name='conformancelevel',
            name='report_params',
        ),
        migrations.DeleteModel(
            name='AuditReportParams',
        ),
    ]
