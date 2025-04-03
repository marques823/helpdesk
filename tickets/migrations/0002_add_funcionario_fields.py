from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='funcionario',
            name='criado_em',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='funcionario',
            name='atualizado_em',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ] 