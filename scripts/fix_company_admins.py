import os
import sys
import django

# Configurar o ambiente Django
sys.path.append('/var/www/app-helpdesk')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk_app.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Funcionario

def fix_company_admins():
    print("Iniciando correção de privilégios de Administradores de Empresa...")
    
    # Encontra todos os funcionários que são 'admin' de empresa
    company_admins = Funcionario.objects.filter(tipo='admin')
    
    fixed_count = 0
    for func in company_admins:
        user = func.usuario
        if user.is_superuser:
            # Preservar o administrador global principal
            if user.id == 1 or user.username == 'admin':
                print(f"Ignorando o usuário '{user.username}' (provavelmente o Administrador Global/Sistema principal).")
                continue
                
            print(f"Revogando 'is_superuser' do usuário: {user.username} (Empresa Admin)")
            user.is_superuser = False
            # Assegurar que ele ainda consegue acessar se tiver is_staff (o save do modelo faria isso)
            user.is_staff = True 
            user.save()
            fixed_count += 1
            
    print(f"Correção concluída. {fixed_count} usuários tiveram privilégios superuser revogados.")

if __name__ == '__main__':
    fix_company_admins()
