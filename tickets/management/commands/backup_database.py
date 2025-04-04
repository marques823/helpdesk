import os
import time
import subprocess
import glob
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Faz backup do banco de dados e gerencia retenção de backups antigos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de dias para reter backups (padrão: 30)'
        )
        parser.add_argument(
            '--email',
            action='store_true',
            help='Enviar backup por email'
        )
        parser.add_argument(
            '--recipients',
            nargs='+',
            help='Lista de destinatários para o email'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            default=True,
            help='Compactar o arquivo de backup'
        )
        parser.add_argument(
            '--no-cleanup',
            action='store_true',
            help='Não limpar backups antigos'
        )

    def handle(self, *args, **options):
        try:
            # Configura diretório de backup
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            # Timestamp para o nome do arquivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Obtendo detalhes do banco de dados atual
            db_settings = settings.DATABASES['default']
            db_name = db_settings['NAME']
            db_engine = db_settings['ENGINE']
            
            # Define o nome do arquivo de backup baseado no engine do banco
            backup_file = None
            if 'sqlite3' in db_engine:
                backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
                self._backup_sqlite(db_name, backup_file)
            elif 'postgresql' in db_engine:
                backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sql')
                self._backup_postgres(db_settings, backup_file)
            elif 'mysql' in db_engine:
                backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sql')
                self._backup_mysql(db_settings, backup_file)
            else:
                self.stdout.write(self.style.ERROR(f'Engine de banco de dados não suportado: {db_engine}'))
                return
            
            # Compacta o arquivo se solicitado
            if options['compress'] and backup_file:
                compressed_file = self._compress_file(backup_file)
                if compressed_file:
                    backup_file = compressed_file
            
            # Envio por email se solicitado
            if options['email'] and options['recipients'] and backup_file:
                self._send_email(backup_file, options['recipients'])
            
            # Limpa backups antigos
            if not options['no_cleanup']:
                self._cleanup_old_backups(backup_dir, options['days'])
            
            # Mensagem de sucesso
            self.stdout.write(self.style.SUCCESS(f'Backup concluído com sucesso: {backup_file}'))
            logger.info(f'Backup concluído com sucesso: {backup_file}')
            
            return backup_file
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao fazer backup: {str(e)}'))
            logger.error(f'Erro ao fazer backup: {str(e)}')
            return None
    
    def _backup_sqlite(self, db_path, backup_path):
        """Faz backup de um banco de dados SQLite."""
        self.stdout.write('Iniciando backup do SQLite...')
        
        # Se o banco estiver em memória, não há como fazer backup
        if db_path == ':memory:':
            self.stdout.write(self.style.WARNING('Não é possível fazer backup de banco em memória (:memory:)'))
            return
        
        # Para SQLite, basta copiar o arquivo
        with connection.cursor():
            connection.connection.commit()  # Assegura que todas as transações estão finalizadas
            
        # Copia o arquivo para o destino
        subprocess.run(['cp', db_path, backup_path], check=True)
        self.stdout.write(self.style.SUCCESS(f'Backup do SQLite concluído: {backup_path}'))
    
    def _backup_postgres(self, db_settings, backup_path):
        """Faz backup de um banco PostgreSQL."""
        self.stdout.write('Iniciando backup do PostgreSQL...')
        
        env = os.environ.copy()
        
        # Configura variáveis de ambiente para a autenticação
        if db_settings.get('USER'):
            env['PGUSER'] = db_settings['USER']
        if db_settings.get('PASSWORD'):
            env['PGPASSWORD'] = db_settings['PASSWORD']
        
        cmd = [
            'pg_dump',
            '--dbname', db_settings['NAME'],
            '--file', backup_path,
            '--format', 'p',  # plain text format
        ]
        
        if db_settings.get('HOST'):
            cmd.extend(['--host', db_settings['HOST']])
        if db_settings.get('PORT'):
            cmd.extend(['--port', str(db_settings['PORT'])])
        
        subprocess.run(cmd, env=env, check=True)
        self.stdout.write(self.style.SUCCESS(f'Backup do PostgreSQL concluído: {backup_path}'))
    
    def _backup_mysql(self, db_settings, backup_path):
        """Faz backup de um banco MySQL."""
        self.stdout.write('Iniciando backup do MySQL...')
        
        cmd = [
            'mysqldump',
            '--result-file', backup_path,
            '--single-transaction',
            '--quick',
        ]
        
        if db_settings.get('USER'):
            cmd.extend(['--user', db_settings['USER']])
        if db_settings.get('PASSWORD'):
            cmd.extend(['--password=' + db_settings['PASSWORD']])
        if db_settings.get('HOST'):
            cmd.extend(['--host', db_settings['HOST']])
        if db_settings.get('PORT'):
            cmd.extend(['--port', str(db_settings['PORT'])])
        
        cmd.append(db_settings['NAME'])
        
        subprocess.run(cmd, check=True)
        self.stdout.write(self.style.SUCCESS(f'Backup do MySQL concluído: {backup_path}'))
    
    def _compress_file(self, file_path):
        """Comprime o arquivo de backup."""
        self.stdout.write('Compactando arquivo de backup...')
        
        compressed_file = file_path + '.gz'
        try:
            subprocess.run(['gzip', '-f', file_path], check=True)
            self.stdout.write(self.style.SUCCESS(f'Arquivo compactado: {compressed_file}'))
            return compressed_file
        except subprocess.SubprocessError as e:
            self.stdout.write(self.style.WARNING(f'Falha ao compactar arquivo: {str(e)}'))
            return file_path
    
    def _send_email(self, file_path, recipients):
        """Envia o backup por email."""
        self.stdout.write('Enviando backup por email...')
        
        try:
            subject = f'Backup do Banco de Dados - {datetime.now().strftime("%d/%m/%Y %H:%M")}'
            message = 'Segue em anexo o backup do banco de dados.'
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients
            )
            
            with open(file_path, 'rb') as f:
                email.attach(os.path.basename(file_path), f.read(), 'application/octet-stream')
                
            email.send()
            self.stdout.write(self.style.SUCCESS(f'Backup enviado para: {", ".join(recipients)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao enviar backup por email: {str(e)}'))
    
    def _cleanup_old_backups(self, backup_dir, days):
        """Remove backups mais antigos que o número de dias especificado."""
        self.stdout.write(f'Limpando backups mais antigos que {days} dias...')
        
        # Calcula o timestamp de corte
        cutoff_time = time.time() - (days * 24 * 3600)
        
        # Busca por arquivos de backup
        backup_files = glob.glob(os.path.join(backup_dir, 'db_backup_*'))
        
        # Remove arquivos mais antigos que o limite
        for file_path in backup_files:
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                self.stdout.write(f'Backup antigo removido: {file_path}')
        
        self.stdout.write(self.style.SUCCESS('Limpeza de backups antigos concluída')) 