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
- Adicionar notas técnicas aos tickets para documentação interna

### Para Administradores de Empresa
- Acesso ao painel administrativo da empresa através do botão "Painel Admin" no dashboard
- Gerenciar usuários da própria empresa
  - Adicionar novos usuários com limites configuráveis
  - Editar informações de usuários existentes
  - Visualizar lista completa de usuários
- Gerenciar categorias de chamados
  - Criar e editar categorias personalizadas
  - Definir ícones e cores para melhor visualização
  - Organizar a ordem de exibição das categorias
- Configurar campos personalizados para chamados
  - Criar campos específicos para a empresa
  - Definir tipos de campo (texto, número, data, seleção)
  - Configurar se o campo é obrigatório
- Visualizar estatísticas específicas da empresa

### Para Administradores do Sistema
- Gerenciar empresas e usuários
- Ter visibilidade de todos os tickets do sistema
- Poder responder e gerenciar qualquer ticket
- Acessar estatísticas gerais do sistema
- Configurar parâmetros globais do sistema

## 3. Boas Práticas
- Manter as descrições dos tickets claras e detalhadas
- Atualizar o status dos tickets conforme o progresso
- Responder aos tickets em tempo hábil
- Usar a prioridade corretamente para indicar urgência
- Manter um histórico de comunicação através dos comentários
- Categorizar corretamente os chamados para facilitar o gerenciamento

## 4. Recursos Disponíveis
- Dashboard com visão geral dos tickets
  - Visualização por categorias
  - Filtros por status, prioridade e empresa
  - Barra de pesquisa avançada
- Interface administrativa para empresas
  - Gerenciamento de usuários
  - Configuração de categorias
  - Campos personalizados
- Sistema de notificações por email
- Histórico completo de interações
- Interface responsiva para acesso em diferentes dispositivos
- Geração de relatórios e estatísticas
- Exportação de chamados em formato PDF

## 5. Novos Recursos (Última Atualização)
- Interface de dashboard aprimorada
  - Cards para acesso rápido às funções administrativas
  - Botão destacado para criação de chamados
  - Melhor organização visual das categorias
- Sistema multi-empresa com isolamento de dados
  - Cada empresa vê apenas seus próprios chamados e usuários
  - Administradores de empresa têm controle sobre suas configurações
- Categorização avançada de chamados
  - Interface visual com ícones e cores personalizáveis
  - Fluxo de navegação por categoria > status > lista de chamados
- Campos personalizados por empresa
  - Cada empresa pode definir campos específicos para seus chamados
  - Suporte a diferentes tipos de campo (texto, número, data, seleção, etc)
- Melhorias no formulário de criação de usuários
  - Interface simplificada para administradores de empresa
  - Validação aprimorada dos dados de usuário

## 6. Manutenção
- Fazer backup regular do banco de dados
- Monitorar o uso do sistema
- Atualizar as dependências quando necessário
- Manter os logs do sistema para diagnóstico

## 7. Segurança
- Usar senhas fortes
- Não compartilhar credenciais
- Fazer logout após o uso
- Manter o sistema atualizado
- Isolamento de dados entre empresas

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