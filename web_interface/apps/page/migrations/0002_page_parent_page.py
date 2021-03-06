# Generated by Django 2.2.5 on 2020-12-15 16:20

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F, IntegerField
from django.db.models.functions import Cast


def migrate_parent_id_to_parent_page(apps, schema_editor):
    Page = apps.get_model('page', 'Page')
    db_alias = schema_editor.connection.alias
    Page.objects.using(db_alias).exclude(parent_id='').update(
        parent_page_id=Cast(F('parent_id'), IntegerField())
    )


class Migration(migrations.Migration):

    dependencies = [
        ('page', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='parent_page',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='page.Page'),
        ),
        migrations.RunPython(migrate_parent_id_to_parent_page),
        migrations.RemoveField(
            model_name='page',
            name='parent_id',
        ),
    ]
