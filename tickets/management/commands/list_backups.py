import os
import glob
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Lista os backups disponíveis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['list', 'table', 'json'],
            default='table',
            help='Formato de saída: list, table ou json (padrão: table)'
        )

    def handle(self, *args, **options):
        try:
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            
            # Se não existe diretório de backups, cria-o
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                self.stdout.write(self.style.WARNING(f'Diretório de backups criado: {backup_dir}'))
                self.stdout.write(self.style.WARNING('Nenhum backup disponível ainda.'))
                return
            
            # Obtém lista de backups
            backup_files = glob.glob(os.path.join(backup_dir, 'db_backup_*'))
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            if not backup_files:
                self.stdout.write(self.style.WARNING('Nenhum backup encontrado.'))
                return
            
            # Formata e imprime a lista de backups
            output_format = options['format']
            if output_format == 'list':
                self._format_list(backup_files)
            elif output_format == 'json':
                self._format_json(backup_files)
            else:  # table (default)
                self._format_table(backup_files)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao listar backups: {str(e)}'))
            logger.error(f'Erro ao listar backups: {str(e)}')
    
    def _format_list(self, backup_files):
        """Formata os backups como uma lista simples."""
        for i, file_path in enumerate(backup_files, 1):
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            mod_time = os.path.getmtime(file_path)
            mod_time_str = self._format_timestamp(mod_time)
            
            self.stdout.write(f'{i}. {os.path.basename(file_path)}')
            self.stdout.write(f'   Tamanho: {size_mb:.2f} MB')
            self.stdout.write(f'   Data: {mod_time_str}')
            self.stdout.write('')
    
    def _format_table(self, backup_files):
        """Formata os backups como uma tabela."""
        # Cabeçalho da tabela
        self.stdout.write(f'{"ID":<4}{"Nome do Arquivo":<45}{"Tamanho":<12}{"Data":<20}')
        self.stdout.write('-' * 81)
        
        # Linhas da tabela
        for i, file_path in enumerate(backup_files, 1):
            filename = os.path.basename(file_path)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            mod_time = os.path.getmtime(file_path)
            mod_time_str = self._format_timestamp(mod_time)
            
            self.stdout.write(f'{i:<4}{filename:<45}{size_mb:.2f} MB{"":<4}{mod_time_str:<20}')
    
    def _format_json(self, backup_files):
        """Formata os backups como JSON."""
        import json
        
        backups = []
        for i, file_path in enumerate(backup_files, 1):
            filename = os.path.basename(file_path)
            size = os.path.getsize(file_path)
            mod_time = os.path.getmtime(file_path)
            
            backups.append({
                'id': i,
                'filename': filename,
                'path': file_path,
                'size_bytes': size,
                'size_mb': round(size / (1024 * 1024), 2),
                'timestamp': mod_time,
                'datetime': self._format_timestamp(mod_time)
            })
        
        self.stdout.write(json.dumps(backups, indent=2))
    
    def _format_timestamp(self, timestamp):
        """Formata um timestamp para exibição."""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%d/%m/%Y %H:%M:%S') 