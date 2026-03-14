import os
import sys
import django
from dotenv import load_dotenv

load_dotenv('/var/www/app-helpdesk/.env')

sys.path.append('/var/www/app-helpdesk')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk_app.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Empresa, Funcionario

def report_users():
    print("=" * 60)
    print("RELATÓRIO DE USUÁRIOS DO SISTEMA")
    print("=" * 60)
    print()
    
    # 1. System Admins (Django superusers)
    print("--- 1. ADMINISTRADORES DE SISTEMA (Visão Global) ---")
    superusers = User.objects.filter(is_superuser=True)
    if superusers.exists():
        for u in superusers:
            print(f" - {u.username} (Email: {u.email or 'N/A'})")
            # Verifica se este superusuário também tem um perfil de funcionário associado
            funcs = Funcionario.objects.filter(usuario=u)
            if funcs.exists():
                func = funcs.first()
                empresas = ", ".join([e.nome for e in func.empresas.all()])
                print(f"   [!] Aviso: Tem perfil de funcionário vinculado: Tipo={func.tipo}, Empresas: {empresas}")
                print("   [!] Superusuários do Django podem ver TUDO independente das empresas vinculadas no perfil de Funcionário.")
    else:
        print(" Nenhum superusuário encontrado.")
    print()
    
    # 2. Users grouped by Company
    print("--- 2. USUÁRIOS POR EMPRESA (Isolamento de Dados) ---")
    empresas = Empresa.objects.all()
    if not empresas.exists():
        print(" Nenhuma empresa cadastrada.")
    
    for empresa in empresas:
        print(f"\nEmpresa: {empresa.nome} (CNPJ: {empresa.cnpj})")
        funcionarios = Funcionario.objects.filter(empresas=empresa)
        if not funcionarios.exists():
            print("  Nenhum usuário associado.")
            continue
            
        # Agrupa os funcionários da empresa por tipo
        admins = funcionarios.filter(tipo='admin')
        suporte = funcionarios.filter(tipo='suporte')
        clientes = funcionarios.filter(tipo='cliente')
        
        if admins.exists():
            print("  - Administradores da Empresa:")
            for a in admins:
                sup_tag = "[SUPERUSER GLOBAL!]" if a.usuario.is_superuser else ""
                print(f"    * {a.usuario.username} {sup_tag}")
                
        if suporte.exists():
            print("  - Suporte/Técnicos:")
            for s in suporte:
                print(f"    * {s.usuario.username}")
                
        if clientes.exists():
            print("  - Clientes:")
            for c in clientes:
                print(f"    * {c.usuario.username}")
    print("\n" + "=" * 60)

if __name__ == '__main__':
    report_users()
