# Generated by Django 3.0.7 on 2021-01-16 21:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0002_processor_nlp_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='processor_nlp',
            name='nlp',
        ),
    ]
