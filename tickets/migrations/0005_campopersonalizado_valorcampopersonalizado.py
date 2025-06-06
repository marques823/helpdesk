# Generated by Django 4.2.7 on 2025-04-03 03:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0004_historicoticket'),
    ]

    operations = [
        migrations.CreateModel(
            name='CampoPersonalizado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('tipo', models.CharField(choices=[('texto', 'Texto'), ('numero', 'Número'), ('data', 'Data'), ('selecao', 'Seleção'), ('checkbox', 'Checkbox')], max_length=20)),
                ('obrigatorio', models.BooleanField(default=False)),
                ('opcoes', models.TextField(blank=True, help_text="Para campos do tipo 'Seleção', insira as opções separadas por vírgula")),
                ('ordem', models.IntegerField(default=0)),
                ('ativo', models.BooleanField(default=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='campos_personalizados', to='tickets.empresa')),
            ],
            options={
                'ordering': ['ordem', 'nome'],
                'unique_together': {('empresa', 'nome')},
            },
        ),
        migrations.CreateModel(
            name='ValorCampoPersonalizado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', models.TextField()),
                ('campo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tickets.campopersonalizado')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='valores_campos_personalizados', to='tickets.ticket')),
            ],
            options={
                'unique_together': {('ticket', 'campo')},
            },
        ),
    ]
