# Generated by Django 4.2.7 on 2025-04-04 01:37

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0013_alter_valorcampopersonalizado_atualizado_em'),
    ]

    operations = [
        migrations.AddField(
            model_name='campopersonalizado',
            name='new_atualizado_em',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
    ]
