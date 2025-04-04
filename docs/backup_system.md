# Sistema de Backup do Banco de Dados

Este documento descreve como usar, configurar e gerenciar o sistema de backup implementado para o aplicativo Helpdesk.

## Funcionalidades

O sistema de backup oferece as seguintes funcionalidades:

- Backup manual através da interface administrativa
- Backup automatizado via cron
- Restauração de backups
- Gerenciamento de retenção de backups antigos
- Suporte para diferentes engines de banco de dados (SQLite, PostgreSQL, MySQL)
- Download de arquivos de backup

## Acessando o Gerenciador de Backups

1. Faça login na interface administrativa do Django (/admin/)
2. No painel lateral, clique em "Gerenciador de Backups" na seção "Ferramentas de Administração"

## Criando Backups Manualmente

1. No Gerenciador de Backups, clique no botão "Criar Novo Backup"
2. O sistema criará um backup do banco de dados atual e o listará na tabela

## Restaurando Backups

1. No Gerenciador de Backups, localize o backup que deseja restaurar
2. Clique no botão "Restaurar" ao lado do backup
3. Confirme a operação na caixa de diálogo

**ATENÇÃO**: A restauração de um backup irá substituir todos os dados atuais no banco de dados!

## Configurando Backups Automáticos com Cron

Para configurar backups automáticos, adicione uma entrada no crontab do sistema:

```bash
# Abrir o editor crontab
crontab -e

# Adicionar uma linha para executar o script de backup
# Exemplo: Todos os dias às 2 da manhã
0 2 * * * /var/www/app-helpdesk/scripts/backup_cron.sh
```

## Personalizando a Configuração de Backup

O script de backup (`backup_cron.sh`) pode ser personalizado:

- Altere o parâmetro `--days` para ajustar o período de retenção dos backups
- Adicione o parâmetro `--email` e `--recipients` para enviar o backup por e-mail

Exemplo:
```bash
python manage.py backup_database --days=60 --email --recipients admin@example.com support@example.com
```

## Comandos de Terminal Úteis

### Criar um backup

```bash
python manage.py backup_database
```

### Listar backups disponíveis

```bash
python manage.py list_backups
```

### Restaurar um backup específico

```bash
python manage.py restore_database /caminho/para/arquivo/backup.sqlite3
```

### Restaurar o backup mais recente

```bash
python manage.py restore_database --latest
```

## Estrutura de Armazenamento

Os backups são armazenados no diretório `backups/` na raiz do projeto. Cada arquivo de backup segue o formato:

```
db_backup_YYYYMMDD_HHMMSS.{extensão}
```

Onde a extensão depende do tipo de banco de dados (.sqlite3 para SQLite, .sql para PostgreSQL/MySQL). 