# Generated by Django 3.0.7 on 2020-12-11 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_mert2'),
    ]

    operations = [
        migrations.CreateModel(
            name='Mert3',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('oldu', models.CharField(max_length=10)),
                ('olmadi', models.CharField(max_length=10)),
            ],
        ),
    ]