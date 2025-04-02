# Guia de Contribuição

## Processo de Desenvolvimento

### 1. Estrutura de Branches
- `main`: Branch principal, contém código estável e pronto para produção
- `develop`: Branch de desenvolvimento, onde novas funcionalidades são integradas
- `feature/*`: Branches para novas funcionalidades
- `bugfix/*`: Branches para correções de bugs
- `hotfix/*`: Branches para correções urgentes em produção

### 2. Fluxo de Trabalho

#### Para Novas Funcionalidades:
1. Criar uma branch a partir de `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/nome-da-funcionalidade
   ```

2. Desenvolver a funcionalidade
3. Fazer commits seguindo o padrão:
   ```
   feat: descrição da funcionalidade
   
   - Detalhe 1
   - Detalhe 2
   ```

4. Fazer pull request para `develop`
5. Após revisão e testes, merge para `develop`

#### Para Correções de Bugs:
1. Criar uma branch a partir de `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b bugfix/nome-do-bug
   ```

2. Corrigir o bug
3. Fazer commits seguindo o padrão:
   ```
   fix: descrição da correção
   
   - Detalhe 1
   - Detalhe 2
   ```

4. Fazer pull request para `develop`
5. Após revisão e testes, merge para `develop`

#### Para Correções Urgentes em Produção:
1. Criar uma branch a partir de `main`:
   ```bash
   git checkout main
   git pull
   git checkout -b hotfix/nome-da-correcao
   ```

2. Implementar a correção
3. Fazer commits seguindo o padrão:
   ```
   hotfix: descrição da correção urgente
   
   - Detalhe 1
   - Detalhe 2
   ```

4. Fazer pull request para `main`
5. Após revisão e testes, merge para `main`
6. Merge também para `develop`

### 3. Versionamento

Seguimos o padrão [Semantic Versioning](https://semver.org/):
- MAJOR: mudanças incompatíveis
- MINOR: novas funcionalidades compatíveis
- PATCH: correções compatíveis

Exemplo: v1.2.3
- 1: MAJOR
- 2: MINOR
- 3: PATCH

### 4. Processo de Release

1. Atualizar a versão no arquivo apropriado
2. Criar uma tag:
   ```bash
   git tag -a v1.2.3 -m "Release v1.2.3"
   git push origin v1.2.3
   ```

3. Criar release no GitHub com changelog

### 5. Padrões de Código

- Seguir PEP 8 para Python
- Documentar funções e classes
- Escrever testes para novas funcionalidades
- Manter o código limpo e organizado

### 6. Checklist para Pull Requests

- [ ] Código segue os padrões estabelecidos
- [ ] Testes foram adicionados/atualizados
- [ ] Documentação foi atualizada
- [ ] Changelog foi atualizado
- [ ] Código foi revisado por outro desenvolvedor

### 7. Ambiente de Desenvolvimento

1. Clonar o repositório:
   ```bash
   git clone https://github.com/marques823/helpdesk.git
   cd helpdesk
   ```

2. Criar ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Instalar dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variáveis de ambiente:
   ```bash
   cp .env.example .env
   # Editar .env com suas configurações
   ```

5. Executar migrações:
   ```bash
   python manage.py migrate
   ```

6. Criar superusuário:
   ```bash
   python manage.py createsuperuser
   ```

7. Iniciar servidor de desenvolvimento:
   ```bash
   python manage.py runserver
   ```

### 8. Testes

- Executar testes:
  ```bash
  python manage.py test
  ```

- Verificar cobertura:
  ```bash
  coverage run --source='.' manage.py test
  coverage report
  ```

### 9. Documentação

- Atualizar README.md para mudanças significativas
- Documentar novas funcionalidades
- Atualizar manual do usuário quando necessário

### 10. Deploy

1. Atualizar versão
2. Fazer merge para main
3. Criar tag
4. Fazer deploy seguindo o processo estabelecido
5. Verificar logs e monitorar 