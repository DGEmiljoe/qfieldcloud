# Generated by Django 3.2.2 on 2021-05-17 10:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0037_alter_project_owner_help_text"),
    ]

    operations = [
        migrations.RenameField(
            model_name="useraccount",
            old_name="workplace",
            new_name="company",
        ),
    ]
