# Documentação da API Helpdesk

Esta documentação detalha os endpoints disponíveis para integração com o aplicativo móvel do Helpdesk.

## Informações Gerais

- **Base URL**: `https://seu-dominio.com/api/`
- **Formato de Dados**: JSON
- **Headers Comuns**:
    - `Content-Type: application/json`
    - `Accept: application/json`

---

## Autenticação

A API suporta dois métodos de autenticação:
1. **Sessão (Cookies)**: Recomendado para o aplicativo móvel após o login.
2. **API Key**: Usado principalmente para integrações externas (n8n). Requer o header `X-API-Key`.

### 1. Login
Realiza a autenticação do usuário.

- **Endpoint**: `POST /auth/login/`
- **Autenticação**: Nenhuma
- **Request Body**:
    ```json
    {
      "username": "seu_usuario",
      "password": "sua_senha"
    }
    ```
- **Resposta (200 OK)**:
    ```json
    {
      "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@exemplo.com",
        "first_name": "Admin",
        "last_name": "Sistema",
        "is_staff": true,
        "is_superuser": true
      }
    }
    ```

### 2. Logout
Encerra a sessão atual.

- **Endpoint**: `POST /auth/logout/`
- **Autenticação**: Sessão

### 3. Obter Usuário Atual
Retorna as informações do usuário logado.

- **Endpoint**: `GET /auth/user/`
- **Autenticação**: Sessão

---

## Dashboard

### 1. Estatísticas do Dashboard
Retorna contadores de tickets e lista de tickets recentes.

- **Endpoint**: `GET /dashboard/stats/`
- **Autenticação**: Sessão
- **Resposta (200 OK)**:
    ```json
    {
      "total_tickets": 10,
      "tickets_abertos": 5,
      "tickets_resolvidos": 3,
      "tickets_urgentes": 2,
      "prioridade_data": {
        "baixa": {"label": "Baixa", "count": 1},
        "media": {"label": "Média", "count": 4},
        "alta": {"label": "Alta", "count": 3},
        "urgente": {"label": "Urgente", "count": 2}
      },
      "categorias": [
        {
          "id": 1,
          "nome": "Suporte Técnico",
          "cor": "blue",
          "total": 5,
          "abertos": 3
        }
      ],
      "tickets": [...] // Lista dos últimos 5 tickets
    }
    ```

---

## Gerenciamento de Tickets (n8n API)

Estes endpoints utilizam autenticação por **API Key** via header `X-API-Key`.

### 1. Listar Tickets
- **Endpoint**: `GET /n8n/tickets/`
- **Parâmetros Query**:
    - `empresa_id` (opcional): Filtrar por ID da empresa.
    - `status` (opcional): Filtrar por status (`aberto`, `em_atendimento`, `resolvido`, `fechado`).
    - `limit` (opcional): Máximo de resultados (padrão 50).

### 2. Detalhes do Ticket
- **Endpoint**: `GET /n8n/tickets/{ticket_id}/`

### 3. Criar Ticket
- **Endpoint**: `POST /n8n/tickets/create/`
- **Request Body**:
    ```json
    {
      "titulo": "Monitor não liga",
      "descricao": "O monitor do setor financeiro parou de funcionar",
      "empresa_id": 1,
      "categoria_id": 2,      // Opcional
      "prioridade": "alta",   // Opcional (baixa, media, alta, urgente)
      "status": "aberto"      // Opcional
    }
    ```

### 4. Atualizar Ticket
- **Endpoint**: `POST /n8n/tickets/{ticket_id}/update/`
- **Campos Editáveis**: `status`, `prioridade`, `atribuido_a_id`, `comentario` (texto), `comentario_publico` (boolean).

### 5. Adicionar Comentário
- **Endpoint**: `POST /n8n/tickets/{ticket_id}/comment/`
- **Request Body**:
    ```json
    {
      "conteudo": "Técnico a caminho do local",
      "publico": true
    }
    ```

---

## Sugestões para Mobile

Para uma experiência mobile superior, considere implementar:
1. **Refresh Automático**: Usar o endpoint de estatísticas para atualizar ícones de notificação.
2. **Push Notifications**: Integração com webhooks (já disponíveis no código via n8n) para alertar sobre novos tickets.
3. **Filtros Rápidos**: Facilitar o acesso a tickets "Urgentes" ou "Abertos" diretamente no dashboard.
