# Generated by Django 4.2.16 on 2025-03-27 01:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('calendarapp', '0006_event_durata'),
    ]

    operations = [
        migrations.CreateModel(
            name='Operatie',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Nume', models.CharField(max_length=255)),
                ('Laparoscopic', models.BooleanField(default=False)),
                ('OperatieCurata', models.BooleanField(default=True)),
                ('NecesitaIntubare', models.BooleanField(default=True)),
            ],
        ),
        migrations.AlterField(
            model_name='event',
            name='tip_operatie',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='calendarapp.operatie'),
        ),
    ]
