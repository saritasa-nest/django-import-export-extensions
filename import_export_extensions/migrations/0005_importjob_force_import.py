# Generated by Django 4.2.7 on 2023-11-16 10:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("import_export_extensions", "0004_alter_exportjob_created_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="importjob",
            name="force_import",
            field=models.BooleanField(
                default=False,
                help_text="Import data with skip ivalid rows.",
                verbose_name="Force import",
            ),
        ),
    ]