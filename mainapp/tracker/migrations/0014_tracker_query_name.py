# Generated by Django 3.0.7 on 2021-01-11 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0013_auto_20210111_0927'),
    ]

    operations = [
        migrations.AddField(
            model_name='tracker',
            name='query_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]