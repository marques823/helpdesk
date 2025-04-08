import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk_app.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Empresa, CategoriaChamado, Funcionario, Ticket

def create_sample_data():
    # Criar empresa
    empresa, _ = Empresa.objects.get_or_create(
        nome='Empresa Exemplo',
        cnpj='12345678901234',
        telefone='(11) 1234-5678',
        email='contato@exemplo.com',
        endereco='Rua Exemplo, 123'
    )

    # Criar categorias
    categorias = [
        ('Suporte Técnico', 'danger', 'fa-wrench'),
        ('Dúvidas', 'info', 'fa-question-circle'),
        ('Bugs', 'warning', 'fa-bug'),
        ('Melhorias', 'success', 'fa-lightbulb'),
        ('Urgente', 'danger', 'fa-exclamation-circle')
    ]

    for i, (nome, cor, icone) in enumerate(categorias):
        CategoriaChamado.objects.get_or_create(
            nome=nome,
            empresa=empresa,
            defaults={
                'cor': cor,
                'icone': icone,
                'ordem': i
            }
        )

    # Criar usuários e funcionários
    # Admin
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@exemplo.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    admin_user.set_password('admin123')
    admin_user.save()

    admin_func, _ = Funcionario.objects.get_or_create(
        usuario=admin_user,
        tipo='admin'
    )
    admin_func.empresas.add(empresa)

    # Suporte
    suporte_user, _ = User.objects.get_or_create(
        username='suporte',
        defaults={
            'email': 'suporte@exemplo.com',
            'is_staff': True
        }
    )
    suporte_user.set_password('suporte123')
    suporte_user.save()

    suporte_func, _ = Funcionario.objects.get_or_create(
        usuario=suporte_user,
        tipo='suporte'
    )
    suporte_func.empresas.add(empresa)

    # Cliente
    cliente_user, _ = User.objects.get_or_create(
        username='cliente',
        defaults={
            'email': 'cliente@exemplo.com'
        }
    )
    cliente_user.set_password('cliente123')
    cliente_user.save()

    cliente_func, _ = Funcionario.objects.get_or_create(
        usuario=cliente_user,
        tipo='cliente'
    )
    cliente_func.empresas.add(empresa)

    # Criar tickets
    status_list = ['aberto', 'em_andamento', 'pendente', 'resolvido', 'fechado']
    prioridade_list = ['baixa', 'media', 'alta', 'urgente']
    categorias = CategoriaChamado.objects.filter(empresa=empresa)
    
    # Criar 20 tickets com datas variadas nos últimos 30 dias
    for i in range(20):
        dias_atras = random.randint(0, 30)
        data_criacao = datetime.now() - timedelta(days=dias_atras)
        
        Ticket.objects.create(
            titulo=f'Ticket de teste #{i+1}',
            descricao=f'Descrição do ticket de teste #{i+1}',
            status=random.choice(status_list),
            prioridade=random.choice(prioridade_list),
            empresa=empresa,
            categoria=random.choice(categorias),
            criado_por=random.choice([admin_user, suporte_user, cliente_user]),
            atribuido_a=random.choice([admin_func, suporte_func, None]),
            criado_em=data_criacao,
            atualizado_em=data_criacao + timedelta(days=random.randint(0, 5))
        )

if __name__ == '__main__':
    print('Criando dados de exemplo...')
    create_sample_data()
    print('Dados de exemplo criados com sucesso!') 