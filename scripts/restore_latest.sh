#!/bin/bash
# Script para restaurar o backup mais recente

# Diretório do projeto
PROJECT_DIR="/var/www/app-helpdesk"

# Ativa o ambiente virtual
source "$PROJECT_DIR/venv/bin/activate"

# Muda para o diretório do projeto
cd "$PROJECT_DIR"

# Configura o DJANGO_SETTINGS_MODULE
export DJANGO_SETTINGS_MODULE=helpdesk_app.settings

# Confirmar antes de restaurar
echo "AVISO: Isso irá substituir todos os dados atuais no banco de dados!"
echo "Deseja continuar? (s/N):"
read confirmation

if [[ "$confirmation" == "s" || "$confirmation" == "S" ]]; then
    # Executa o comando de restauração com o backup mais recente
    python manage.py restore_database --latest --force
    echo "Restauração concluída em $(date)"
else
    echo "Operação cancelada pelo usuário."
fi

# Desativa o ambiente virtual
deactivate 