# Generated by Django 4.2.20 on 2025-07-19 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='device_id',
            field=models.CharField(blank=True, max_length=5000, unique=True, verbose_name='DeviceId'),
        ),
    ]
