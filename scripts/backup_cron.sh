#!/bin/bash
# Script para ser executado via cron para fazer backups automáticos

# Diretório do projeto
PROJECT_DIR="/var/www/app-helpdesk"

# Ativa o ambiente virtual
source "$PROJECT_DIR/venv/bin/activate"

# Muda para o diretório do projeto
cd "$PROJECT_DIR"

# Configura o DJANGO_SETTINGS_MODULE
export DJANGO_SETTINGS_MODULE=helpdesk_app.settings

# Executa o comando de backup
# Por padrão, mantém backups por 30 dias
python manage.py backup_database --days=30

# Desativa o ambiente virtual
deactivate

# Logs
mkdir -p "$PROJECT_DIR/logs"
echo "Backup realizado em $(date)" >> "$PROJECT_DIR/logs/backup.log" 