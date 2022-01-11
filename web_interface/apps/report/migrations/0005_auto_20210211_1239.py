# Generated by Django 2.2.5 on 2021-02-11 12:39

from django.db import migrations, models
import django.db.models.deletion


def migrate_m2m_field(apps, schema_editor):
    ConformanceLevel = apps.get_model('report', 'ConformanceLevel')
    db_alias = schema_editor.connection.alias
    conformance_levels = ConformanceLevel.objects.using(db_alias).all()
    for conformance_level in conformance_levels:
        conformance_level.issues.add(*conformance_level.issue_groups.all())


class Migration(migrations.Migration):

    dependencies = [
        ('framework_data', '0004_auto_20210201_1500'),
        ('issue', '0002_auto_20210211_1239'),
        ('report', '0004_rename_field_issue_group_to_issue_groups'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConformanceLevelIssue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conformance_level',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conformance_level_issues',
                                   to='report.ConformanceLevel')),
                ('issue',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conformance_level_issues',
                                   to='report.IssueGroup')),
            ],
            options={
                'db_table': 'conformance_level_issue',
            },
        ),
        migrations.AddField(
            model_name='conformancelevel',
            name='issues',
            field=models.ManyToManyField(related_name='conformance_levels', through='report.ConformanceLevelIssue',
                                         to='report.IssueGroup'),
        ),
        migrations.RunPython(migrate_m2m_field),
        migrations.RenameModel(
            old_name='IssueGroup',
            new_name='Issue',
        ),
    ]