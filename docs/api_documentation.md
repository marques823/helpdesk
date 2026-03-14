# Documentação da API Helpdesk (Mobile-Ready)

Esta API foi otimizada para integração com o aplicativo móvel em **React**.

## Informações Gerais

- **Base URL**: `https://seu-dominio.com/api/`
- **Autenticação**:
    - **Sessão**: Use para o aplicativo mobile (Login via `/auth/login/`). Credenciais são mantidas via Cookies.
    - **API Key**: Use para integrações externas (Header `X-API-Key`).

---

## Autenticação

### 1. Login
`POST /auth/login/`
- Request: `{"username": "...", "password": "..."}`
- Response: Informações do usuário.

### 2. Logout
`POST /auth/logout/`

### 3. Usuário Atual
`GET /auth/user/`

---

## Metadados (Para Criação de Tickets)

Estes endpoints são essenciais para popular seletores (dropdowns) no aplicativo.

### 1. Listar Empresas
`GET /meta/companies/`
- Retorna empresas que o usuário pode acessar.

### 2. Listar Categorias
`GET /meta/categories/?empresa_id={id}`
- Retorna categorias da empresa selecionada.

### 3. Listar Funcionários
`GET /meta/employees/?empresa_id={id}`
- Retorna funcionários da empresa para atribuição (técnicos).

---

## Gerenciamento de Tickets (Mobile - Via Sessão)

Endpoints otimizados para o fluxo do usuário logado no App.

### 1. Listar Meus Tickets
`GET /mobile/tickets/`
- Retorna tickets criados pelo usuário ou atribuídos a ele.

### 2. Detalhes do Ticket
`GET /mobile/tickets/{id}/`
- Retorna detalhes e lista de comentários.

### 3. Criar Novo Ticket
`POST /mobile/tickets/create/`
- Payload:
    ```json
    {
      "titulo": "...",
      "descricao": "...",
      "empresa_id": 1,
      "categoria_id": 2,
      "prioridade": "media"
    }
    ```

### 4. Adicionar Comentário
`POST /mobile/tickets/{id}/comment/`
- Payload: `{"texto": "..."}`

---

## Dashboard

### 1. Estatísticas
`GET /dashboard/stats/`
- Resumo de tickets abertos, resolvidos e urgentes.
