import os
import glob
import subprocess
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, FileResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import path
from django.core.management import call_command
from django.contrib import messages
from django.utils.html import format_html
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import datetime
import json
import logging
from .models import Ticket, Empresa, Funcionario
from .api.n8n import send_webhook_to_n8n

@staff_member_required
def backup_manager(request):
    """View para gerenciar backups do banco de dados."""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    # Cria o diretório de backups se não existir
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Ação de criar backup
    if request.method == 'POST' and 'action' in request.POST:
        action = request.POST['action']
        
        if action == 'create_backup':
            try:
                backup_file = call_command('backup_database')
                if backup_file:
                    messages.success(request, f'Backup criado com sucesso: {os.path.basename(backup_file)}')
                else:
                    messages.error(request, 'Erro ao criar backup. Verifique os logs para mais detalhes.')
            except Exception as e:
                messages.error(request, f'Erro ao criar backup: {str(e)}')
        
        elif action == 'delete_backup' and 'backup_id' in request.POST:
            backup_id = request.POST['backup_id']
            backups = _get_backups_list(backup_dir)
            
            if 0 <= int(backup_id) < len(backups):
                file_path = backups[int(backup_id)]['path']
                try:
                    os.remove(file_path)
                    messages.success(request, f'Backup excluído: {os.path.basename(file_path)}')
                except Exception as e:
                    messages.error(request, f'Erro ao excluir backup: {str(e)}')
            else:
                messages.error(request, 'ID de backup inválido.')
        
        elif action == 'restore_backup' and 'backup_id' in request.POST:
            backup_id = request.POST['backup_id']
            backups = _get_backups_list(backup_dir)
            
            if 0 <= int(backup_id) < len(backups):
                file_path = backups[int(backup_id)]['path']
                try:
                    if os.path.exists(file_path):
                        # A restauração é feita em um processo separado para evitar problemas com conexões
                        call_command('restore_database', file_path, force=True)
                        messages.success(request, f'Banco de dados restaurado a partir de: {os.path.basename(file_path)}')
                    else:
                        messages.error(request, f'Arquivo de backup não encontrado: {file_path}')
                except Exception as e:
                    messages.error(request, f'Erro ao restaurar backup: {str(e)}')
            else:
                messages.error(request, 'ID de backup inválido.')
    
    # Obtém lista de backups
    backups = _get_backups_list(backup_dir)
    
    # Obtém informações do banco de dados atual
    db_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]
    db_name = settings.DATABASES['default']['NAME']
    
    context = {
        'backups': backups,
        'db_engine': db_engine,
        'db_name': db_name,
        'disk_usage': _get_disk_usage()
    }
    
    return render(request, 'admin/backup_manager.html', context)

@staff_member_required
def download_backup(request, backup_id):
    """Download de um arquivo de backup."""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = _get_backups_list(backup_dir)
    
    try:
        backup_id = int(backup_id)
        if 0 <= backup_id < len(backups):
            file_path = backups[backup_id]['path']
            if os.path.exists(file_path):
                response = FileResponse(open(file_path, 'rb'))
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
    except (ValueError, IndexError) as e:
        pass
    
    return HttpResponse('Backup não encontrado.', status=404)

def _get_backups_list(backup_dir):
    """Retorna uma lista de arquivos de backup ordenados por data (mais recente primeiro)."""
    backup_files = glob.glob(os.path.join(backup_dir, 'db_backup_*'))
    backup_files.sort(key=os.path.getmtime, reverse=True)
    
    backups = []
    for i, file_path in enumerate(backup_files):
        from datetime import datetime
        
        filename = os.path.basename(file_path)
        size_bytes = os.path.getsize(file_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        modified_time = os.path.getmtime(file_path)
        modified_time_str = datetime.fromtimestamp(modified_time).strftime('%d/%m/%Y %H:%M:%S')
        
        backups.append({
            'id': i,
            'filename': filename,
            'path': file_path,
            'size_bytes': size_bytes,
            'size_mb': size_mb,
            'modified_time': modified_time,
            'modified_time_str': modified_time_str
        })
    
    return backups

def _get_disk_usage():
    """Obtém informações sobre o uso de disco."""
    try:
        if os.name == 'posix':  # Linux/Unix
            df = subprocess.run(['df', '-h', settings.BASE_DIR], capture_output=True, text=True, check=True)
            lines = df.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    return {
                        'total': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'percent_used': parts[4]
                    }
        elif os.name == 'nt':  # Windows
            import shutil
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            total_gb = round(total / (1024**3), 2)
            used_gb = round(used / (1024**3), 2)
            free_gb = round(free / (1024**3), 2)
            percent_used = round((used / total) * 100, 1)
            
            return {
                'total': f"{total_gb}G",
                'used': f"{used_gb}G",
                'available': f"{free_gb}G",
                'percent_used': f"{percent_used}%"
            }
    except Exception:
        pass
    
    return {
        'total': 'N/A',
        'used': 'N/A',
        'available': 'N/A',
        'percent_used': 'N/A'
    }

@staff_member_required
def n8n_settings(request):
    """
    View para gerenciar configurações de integração com n8n
    """
    # Obter as configurações atuais
    webhook_enabled = getattr(settings, 'N8N_WEBHOOK_ENABLED', False)
    webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', '')
    
    if request.method == 'POST':
        # Processar o formulário
        webhook_enabled = 'webhook_enabled' in request.POST
        webhook_url = request.POST.get('webhook_url', '')
        
        # Salvar as configurações em variáveis de ambiente
        os.environ['N8N_WEBHOOK_ENABLED'] = 'true' if webhook_enabled else 'false'
        os.environ['N8N_WEBHOOK_URL'] = webhook_url
        
        # Atualizar as configurações no settings
        settings.N8N_WEBHOOK_ENABLED = webhook_enabled
        settings.N8N_WEBHOOK_URL = webhook_url
        
        messages.success(request, 'Configurações do n8n atualizadas com sucesso.')
        
    context = {
        'webhook_enabled': webhook_enabled,
        'webhook_url': webhook_url
    }
    
    return render(request, 'tickets/admin/n8n_settings.html', context)

@staff_member_required
def n8n_test_webhook(request):
    """
    View para testar o webhook do n8n
    """
    if request.method == 'POST':
        event_type = request.POST.get('event_type', 'ticket_created')
        
        # Dados de teste
        test_data = {
            'test': True,
            'timestamp': datetime.datetime.now().isoformat(),
            'sender': request.user.username,
            'message': f'Teste de evento {event_type} enviado manualmente'
        }
        
        # Adicionar dados específicos do tipo de evento
        if event_type == 'ticket_created' or event_type == 'ticket_updated':
            # Obter um ticket aleatório para teste, se existir
            ticket = Ticket.objects.filter(empresa__isnull=False).first()
            if ticket:
                test_data['ticket'] = {
                    'id': ticket.id,
                    'numero_empresa': ticket.numero_empresa,
                    'titulo': ticket.titulo,
                    'status': ticket.status
                }
                
        # Enviar o webhook
        success = send_webhook_to_n8n(event_type, test_data)
        
        if success:
            messages.success(request, f'Evento de teste {event_type} enviado com sucesso para o n8n.')
        else:
            messages.error(request, f'Falha ao enviar evento de teste {event_type} para o n8n. Verifique as configurações e os logs.')
            
    return redirect('tickets:n8n_settings') 