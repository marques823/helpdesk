#!/bin/bash
echo "Parando o serviço helpdesk..."
sudo systemctl stop helpdesk.service
echo "Serviço parado."

echo "Certificando-se de que estamos na branch main..."
cd /var/www/app-helpdesk && git checkout main
echo "Branch atual: $(git branch --show-current)"

echo "Iniciando o serviço helpdesk..."
sudo systemctl start helpdesk.service
echo "Serviço iniciado."

echo "Status do serviço:"
sudo systemctl status helpdesk.service | head -n 5 