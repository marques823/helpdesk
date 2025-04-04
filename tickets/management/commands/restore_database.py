import os
import subprocess
import logging
import glob
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Restaura o banco de dados a partir de um arquivo de backup'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            nargs='?',
            help='Caminho do arquivo de backup a ser restaurado. Se não especificado, lista os backups disponíveis.'
        )
        parser.add_argument(
            '--latest',
            action='store_true',
            help='Restaura o backup mais recente disponível'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Não pede confirmação antes de restaurar'
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
            
            # Lista backups disponíveis se não for especificado um arquivo
            if not options['backup_file'] and not options['latest']:
                self._list_backups(backup_dir)
                return
            
            # Encontra o backup mais recente se solicitado
            backup_file = options['backup_file']
            if options['latest']:
                backup_file = self._get_latest_backup(backup_dir)
                if not backup_file:
                    self.stdout.write(self.style.ERROR('Nenhum backup encontrado.'))
                    return
            
            # Verifica se o arquivo existe
            if not os.path.isfile(backup_file):
                # Tenta encontrar dentro do diretório de backups
                potential_file = os.path.join(backup_dir, os.path.basename(backup_file))
                if os.path.isfile(potential_file):
                    backup_file = potential_file
                else:
                    self.stdout.write(self.style.ERROR(f'Arquivo de backup não encontrado: {backup_file}'))
                    self._list_backups(backup_dir)
                    return
            
            # Confirmação antes de restaurar, a menos que --force seja especificado
            if not options['force']:
                confirm = input(f'AVISO: Isso irá substituir todos os dados. Continuar? (s/N): ')
                if confirm.lower() != 's':
                    self.stdout.write(self.style.WARNING('Operação cancelada pelo usuário.'))
                    return
            
            # Descompacta o arquivo se estiver compactado
            if backup_file.endswith('.gz'):
                backup_file = self._decompress_file(backup_file)
            
            # Determina o engine de banco de dados e chama o método apropriado
            db_settings = settings.DATABASES['default']
            db_engine = db_settings['ENGINE']
            
            if 'sqlite3' in db_engine:
                self._restore_sqlite(backup_file, db_settings['NAME'])
            elif 'postgresql' in db_engine:
                self._restore_postgres(backup_file, db_settings)
            elif 'mysql' in db_engine:
                self._restore_mysql(backup_file, db_settings)
            else:
                self.stdout.write(self.style.ERROR(f'Engine de banco de dados não suportado: {db_engine}'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'Banco de dados restaurado com sucesso a partir de: {backup_file}'))
            logger.info(f'Banco de dados restaurado com sucesso a partir de: {backup_file}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao restaurar o banco de dados: {str(e)}'))
            logger.error(f'Erro ao restaurar o banco de dados: {str(e)}', exc_info=True)
    
    def _list_backups(self, backup_dir):
        """Lista os backups disponíveis."""
        self.stdout.write('Backups disponíveis:')
        
        backup_files = glob.glob(os.path.join(backup_dir, 'db_backup_*'))
        backup_files.sort(key=os.path.getmtime, reverse=True)
        
        if not backup_files:
            self.stdout.write(self.style.WARNING('Nenhum backup encontrado.'))
            return
        
        for i, file_path in enumerate(backup_files, 1):
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            mod_time = os.path.getmtime(file_path)
            mod_time_str = self._format_timestamp(mod_time)
            
            self.stdout.write(f'{i}. {os.path.basename(file_path)}')
            self.stdout.write(f'   Tamanho: {size_mb:.2f} MB')
            self.stdout.write(f'   Data: {mod_time_str}')
            self.stdout.write('')
    
    def _get_latest_backup(self, backup_dir):
        """Retorna o backup mais recente disponível."""
        backup_files = glob.glob(os.path.join(backup_dir, 'db_backup_*'))
        if not backup_files:
            return None
        
        return max(backup_files, key=os.path.getmtime)
    
    def _format_timestamp(self, timestamp):
        """Formata um timestamp para exibição."""
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    
    def _decompress_file(self, file_path):
        """Descompacta um arquivo gzip."""
        self.stdout.write(f'Descompactando arquivo: {file_path}')
        
        # Extrai o arquivo
        try:
            output_file = file_path[:-3]  # Remove .gz
            subprocess.run(['gunzip', '-c', file_path], stdout=open(output_file, 'wb'), check=True)
            self.stdout.write(self.style.SUCCESS(f'Arquivo descompactado: {output_file}'))
            return output_file
        except subprocess.SubprocessError as e:
            raise CommandError(f'Erro ao descompactar arquivo: {str(e)}')
    
    def _restore_sqlite(self, backup_file, db_path):
        """Restaura um banco de dados SQLite."""
        self.stdout.write('Iniciando restauração do SQLite...')
        
        # Fecha todas as conexões
        connection.close()
        
        # Faz cópia de segurança do banco atual
        if os.path.exists(db_path) and db_path != ':memory:':
            backup_path = db_path + '.bak'
            subprocess.run(['cp', db_path, backup_path], check=True)
            self.stdout.write(f'Backup do banco atual criado: {backup_path}')
        
        # Copia o arquivo de backup para o destino
        subprocess.run(['cp', backup_file, db_path], check=True)
        self.stdout.write(self.style.SUCCESS(f'Banco SQLite restaurado: {db_path}'))
    
    def _restore_postgres(self, backup_file, db_settings):
        """Restaura um banco de dados PostgreSQL."""
        self.stdout.write('Iniciando restauração do PostgreSQL...')
        
        env = os.environ.copy()
        
        # Configura variáveis de ambiente para a autenticação
        if db_settings.get('USER'):
            env['PGUSER'] = db_settings['USER']
        if db_settings.get('PASSWORD'):
            env['PGPASSWORD'] = db_settings['PASSWORD']
        
        # Primeiro, recria o banco de dados
        self._recreate_postgres_db(db_settings, env)
        
        # Restaura o banco a partir do backup
        cmd = [
            'psql',
            '--dbname', db_settings['NAME'],
            '--file', backup_file,
        ]
        
        if db_settings.get('HOST'):
            cmd.extend(['--host', db_settings['HOST']])
        if db_settings.get('PORT'):
            cmd.extend(['--port', str(db_settings['PORT'])])
        
        subprocess.run(cmd, env=env, check=True)
        self.stdout.write(self.style.SUCCESS('Banco PostgreSQL restaurado com sucesso'))
    
    def _recreate_postgres_db(self, db_settings, env):
        """Recria o banco de dados PostgreSQL."""
        db_name = db_settings['NAME']
        
        # Comando para se conectar ao banco postgres (padrão)
        connect_cmd = [
            'psql',
            '--dbname', 'postgres',
        ]
        
        if db_settings.get('HOST'):
            connect_cmd.extend(['--host', db_settings['HOST']])
        if db_settings.get('PORT'):
            connect_cmd.extend(['--port', str(db_settings['PORT'])])
        
        # Cria o script SQL temporário para recriar o banco
        sql_file = 'recreate_db.sql'
        with open(sql_file, 'w') as f:
            f.write(f"DROP DATABASE IF EXISTS {db_name};\n")
            f.write(f"CREATE DATABASE {db_name};\n")
        
        # Executa o script
        connect_cmd.extend(['--file', sql_file])
        subprocess.run(connect_cmd, env=env, check=True)
        
        # Remove o arquivo temporário
        os.remove(sql_file)
    
    def _restore_mysql(self, backup_file, db_settings):
        """Restaura um banco de dados MySQL."""
        self.stdout.write('Iniciando restauração do MySQL...')
        
        # Comando para restaurar o banco
        cmd = [
            'mysql',
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
        
        # Executa o comando redirecionando o arquivo para a entrada padrão
        with open(backup_file, 'rb') as f:
            subprocess.run(cmd, stdin=f, check=True)
        
        self.stdout.write(self.style.SUCCESS('Banco MySQL restaurado com sucesso')) 