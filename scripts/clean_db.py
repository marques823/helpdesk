import os
import sys
import django
from dotenv import load_dotenv

# Carrega as variáveis do .env explicitamente
load_dotenv('/var/www/app-helpdesk/.env')

sys.path.append('/var/www/app-helpdesk')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk_app.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Empresa, Funcionario, Ticket, CategoriaChamado, EmpresaConfig

def clean_database():
    print("Iniciando limpeza do banco de dados para testes...")
    
    # Exclui todos os tickets primeiro para evitar problemas de foreign key
    tickets_count = Ticket.objects.count()
    Ticket.objects.all().delete()
    print(f"- {tickets_count} Tickets removidos.")
    
    # Exclui Categorias
    categorias_count = CategoriaChamado.objects.count()
    CategoriaChamado.objects.all().delete()
    print(f"- {categorias_count} Categorias removidas.")
    
    # Exclui Configurações de Empresa
    config_count = EmpresaConfig.objects.count()
    EmpresaConfig.objects.all().delete()
    print(f"- {config_count} Configurações de Empresa removidas.")
    
    # Exclui Empresas
    empresas_count = Empresa.objects.count()
    Empresa.objects.all().delete()
    print(f"- {empresas_count} Empresas removidas.")
    
    # Exclui todos os usuários exceto o 'admin'
    admin_user = User.objects.filter(username='admin').first()
    
    if admin_user:
        usuarios_excluir = User.objects.exclude(id=admin_user.id)
        users_count = usuarios_excluir.count()
        usuarios_excluir.delete()
        print(f"- {users_count} Usuários (e seus perfis de Funcionário) removidos.")
        
        # Garante que o Admin não esteja associado a nenhum perfil residual de funcionário,
        # já que excluímos as empresas
        Funcionario.objects.filter(usuario=admin_user).delete()
        print("- Perfil de funcionário do admin resetado.")
    else:
        print("Aviso: Usuário 'admin' não encontrado! Nenhum usuário foi excluído para evitar perda de acesso.")
        
    print("\n✅ Limpeza concluída com sucesso. O sistema agora só possui o usuário 'admin'.")

if __name__ == '__main__':
    clean_database()
