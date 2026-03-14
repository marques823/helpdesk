import os
import sys
import django

sys.path.append('/var/www/app-helpdesk')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk_app.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Empresa, Funcionario
import uuid

def test_permissions():
    print("Testing functionality of Company Admins...")
    
    # Create test company
    empresa = Empresa.objects.create(
        nome=f"Empresa Teste {uuid.uuid4().hex[:8]}",
        cnpj=f"{uuid.uuid4().hex[:14]}",
        email="teste@empresa.com",
        telefone="11999999999"
    )
    
    # Create test user
    username = f"admin_teste_{uuid.uuid4().hex[:8]}"
    user = User.objects.create_user(username=username, password="password123")
    
    # Create Company Admin
    funcionario = Funcionario.objects.create(
        usuario=user,
        tipo='admin'
    )
    funcionario.empresas.add(empresa)
    
    # Fetch from DB to ensure save() logic activated
    user.refresh_from_db()
    
    print(f"User '{user.username}' created as 'admin'.")
    print(f"is_staff: {user.is_staff}")
    print(f"is_superuser: {user.is_superuser}")
    
    if user.is_staff and not user.is_superuser:
        print("SUCCESS: Company admin correctly configured as staff but not superuser.")
    else:
        print("FAILURE: Permissions are incorrect.")

    # Cleanup
    user.delete()
    empresa.delete()
    print("Cleanup successful.")

if __name__ == '__main__':
    test_permissions()
