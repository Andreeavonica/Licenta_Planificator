# Generated by Django 4.2.16 on 2025-03-27 01:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('calendarapp', '0007_operatie_alter_event_tip_operatie'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='tip_operatie',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evenimente', to='calendarapp.operatie'),
        ),
    ]
