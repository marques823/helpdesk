# Sistema de Helpdesk - Manual de Uso

## 1. Configuração Inicial (Administrador)

### Acesso ao Painel Administrativo
- Acessar `/admin` com o usuário admin
- Criar uma empresa para o cliente
- Criar usuários para os funcionários da empresa
- Associar os usuários como funcionários da empresa, definindo seus tipos:
  - `admin`: Acesso total ao sistema
  - `suporte`: Pode ver e responder tickets da sua empresa
  - `cliente`: Pode criar e ver seus próprios tickets

## 2. Fluxo de Trabalho

### Para Clientes
- Acessar o sistema com suas credenciais
- Criar novos tickets através do botão "Novo Ticket"
- Preencher os campos obrigatórios:
  - Assunto
  - Descrição detalhada
  - Prioridade
- Acompanhar o status dos tickets no dashboard
- Responder aos tickets quando solicitado pelo suporte

### Para Suporte
- Acessar o sistema com suas credenciais
- Ver todos os tickets da sua empresa no dashboard
- Responder aos tickets existentes
- Atualizar o status dos tickets (Aberto, Em Andamento, Fechado)
- Priorizar tickets baseado na urgência

### Para Administradores
- Gerenciar empresas e usuários
- Ter visibilidade de todos os tickets do sistema
- Poder responder e gerenciar qualquer ticket
- Acessar estatísticas gerais do sistema

## 3. Boas Práticas
- Manter as descrições dos tickets claras e detalhadas
- Atualizar o status dos tickets conforme o progresso
- Responder aos tickets em tempo hábil
- Usar a prioridade corretamente para indicar urgência
- Manter um histórico de comunicação através dos comentários

## 4. Recursos Disponíveis
- Dashboard com visão geral dos tickets
- Filtros por status e prioridade
- Sistema de notificações por email
- Histórico completo de interações
- Interface responsiva para acesso em diferentes dispositivos

## 5. Manutenção
- Fazer backup regular do banco de dados
- Monitorar o uso do sistema
- Atualizar as dependências quando necessário
- Manter os logs do sistema para diagnóstico

## 6. Segurança
- Usar senhas fortes
- Não compartilhar credenciais
- Fazer logout após o uso
- Manter o sistema atualizado

## Requisitos do Sistema
- Python 3.8+
- Django 4.2+
- PostgreSQL 13+
- Gunicorn
- Nginx (recomendado)

## Instalação
1. Clonar o repositório
2. Criar ambiente virtual: `python -m venv venv`
3. Ativar ambiente virtual: `source venv/bin/activate`
4. Instalar dependências: `pip install -r requirements.txt`
5. Configurar variáveis de ambiente
6. Executar migrações: `python manage.py migrate`
7. Criar superusuário: `python manage.py createsuperuser`
8. Iniciar servidor: `gunicorn -c gunicorn_config.py helpdesk_app.wsgi:application`

## Suporte
Para suporte técnico ou dúvidas, entre em contato com o administrador do sistema. 