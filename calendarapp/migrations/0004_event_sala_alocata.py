# Generated by Django 4.2.16 on 2025-03-16 03:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendarapp', '0003_event_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='sala_alocata',
            field=models.CharField(blank=True, default='Nicio informatie', max_length=20, null=True),
        ),
    ]
