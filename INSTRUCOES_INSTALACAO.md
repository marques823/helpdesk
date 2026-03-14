# Guia de Instalação e Configuração (Helpdesk)

Este documento descreve os passos necessários para configurar o ambiente do aplicativo Helpdesk do zero em um novo servidor ou máquina de desenvolvimento, já utilizando o **Supabase (PostgreSQL)** como banco de dados.

## 1. Pré-Requisitos

- **Python 3.12** (ou versão 3.10+)
- **Git** (opcional, para controle de versão)
- Acesso à internet para instalar pacotes via `pip`
- Credenciais de acesso ao projeto no **Supabase**

---

## 2. Preparação do Ambiente

### 2.1. Clonar ou Copiar os Arquivos
Coloque todos os arquivos do projeto no diretório desejado (ex: `/var/www/app-helpdesk`):
```bash
cd /var/www/app-helpdesk
```

### 2.2. Criação do Ambiente Virtual (Virtualenv)
É altamente recomendado rodar a aplicação isolada para não conflitar com bibliotecas do sistema operacional.
```bash
python3 -m venv venv
```

Ative o ambiente virtual:
- **No Linux/Mac:**
  ```bash
  source venv/bin/activate
  ```
- **No Windows:**
  ```cmd
  venv\Scripts\activate
  ```

### 2.3. Instalação das Dependências
Com o ambiente ativado (verifique se aparece `(venv)` no seu terminal), instale os pacotes necessários:
```bash
pip install -r requirements.txt
```
> **Nota:** Certifique-se de que o pacote `dj-database-url` e `psycopg2` (ou `psycopg2-binary`) estão instalados no seu `requirements.txt`. Eles são cruciais para a conexão com o Supabase.

---

## 3. Variáveis de Ambiente (.env)

O sistema utiliza o arquivo `.env` para gerenciar chaves e as conexões de banco de forma segura (sem expor no código-fonte). 

Crie um arquivo chamado `.env` na raiz do projeto e preencha com as suas definições. Exemplo base:

```ini
# Segurança
SECRET_KEY=sua-chave-super-secreta-do-django-aqui
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,seu-dominio.com

# Email (Ex: Amazon SES)
EMAIL_ENABLED=True
EMAIL_HOST=email-smtp.sa-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=SUA_CHAVE_AWS_USER
EMAIL_HOST_PASSWORD=SUA_CHAVE_AWS_PASS
DEFAULT_FROM_EMAIL=suportetecnicolitoral@gmail.com

# Banco de Dados (Supabase PostgreSQL)
DATABASE_URL="postgresql://postgres.[ID_DO_PROJETO]:[SUA_SENHA_FORTE]@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
```

### ⚠️ Atenção Especial ao Supabase (Connection Pooling)
Como muitos servidores não suportam **IPv6** nativamente, a conexão direta com o Supabase (iniciada com `db.ID_DO_PROJETO...`) pode retornar o erro `"Network is unreachable"`.
Sempre utilize o **Session Pooler (IPv4)** que o Supabase fornece:
1. No painel inicial do Supabase, clique em **Connect**.
2. Vá para a aba **Session pooler** (Session mode ligado, Porta **5432**).
3. Copie o host fornecido (ex: `aws-1-us-east-1.pooler.supabase.com`). O usuário também deve ter o ID do projeto atrelado: `postgres.[ID_O_PROJETO]`.

---

## 4. Banco de Dados Inicial

Se o banco de dados no Supabase for novo, você precisará recriar as tabelas do Django na nuvem:

```bash
python manage.py migrate
```

### 4.1. Importação de Dados (Opcional)
Se você possui um backup anterior em JSON (`dados_migration.json`), você pode populá-lo com:
```bash
python manage.py loaddata dados_migration.json
```
> Os _Signals_ responsáveis pela automação dos usuários já estão preparados para não executar lógicas duplicadas ao receber carga pelo `loaddata`.

### 4.2. Usuário Administrador
Se esta for uma base completamente zerada, você precisará criar o primeiro administrador para acessar o painel:
```bash
python manage.py createsuperuser
```

---

## 5. Rodando a Aplicação (Desenvolvimento)

Com o banco configurado e as tabelas criadas, você já pode inicializar o servidor de desenvolvimento:

```bash
python manage.py runserver 0.0.0.0:8000
```
O aplicativo já estará disponível em `http://localhost:8000` (ou no IP local/domínio).

## 6. Produção (Servidor)
Em um ambiente de produção real, certifique-se de:
1. Definir `DEBUG=False` no seu `.env`
2. Utilizar um servidor robusto como **Gunicorn** + **Nginx**
3. Consolidar os arquivos estáticos:
   ```bash
   python manage.py collectstatic
   ```
