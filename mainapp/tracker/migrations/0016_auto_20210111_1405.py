# Generated by Django 3.0.7 on 2021-01-11 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0015_auto_20210111_1356'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tracker',
            name='frequency_level2',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
