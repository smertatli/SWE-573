# Generated by Django 3.0.7 on 2021-01-14 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='processor_nlp',
            name='name',
            field=models.CharField(blank=True, max_length=10000, null=True),
        ),
    ]
