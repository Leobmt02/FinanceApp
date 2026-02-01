# Guia de Deploy - FinanceApp no Easypanel

O Easypanel é uma ótima escolha para gerenciar o FinanceApp. Como nossa aplicação é dividida em Backend (API) e Frontend (Interface), criaremos dois serviços (Apps) dentro de um projeto no Easypanel.

## Passo 1: Preparar o Código

O jeito mais fácil de usar o Easypanel é conectando ao **GitHub**.
1. Crie um repositório privado no seu GitHub (ex: `meu-financeapp`).
2. Extraia o conteúdo do ZIP e suba todos os arquivos para este repositório.
   - A estrutura deve ficar com as pastas `backend/` e `frontend/` na raiz do repo.

## Passo 2: Criar Projeto no Easypanel

1. Acesse seu Easypanel.
2. Crie um novo **Project** chamado `FinanceApp`.

## Passo 3: Criar o Serviço Backend (API)

1. Dentro do projeto, clique em **+ Service** e escolha **App**.
2. Nomeie como `backend`.
3. Em **Source**:
   - Conecte seu GitHub e selecione o repositório.
   - **Build Context**: Digite `/backend` (Isso é muito importante, pois diz para usar o Dockerfile da pasta backend).
4. Em **Environment** (Variáveis de Ambiente):
   - Clique em "Edit Environment" e adicione:
     ```
     DATABASE_URL=sqlite:///./data/financeapp.db
     SECRET_KEY=crie-uma-senha-secreta-aqui
     ACCESS_TOKEN_EXPIRE_MINUTES=60
     ```
5. Em **Storage** (Persistência de Dados):
   - Adicione um volume para não perder o banco de dados.
   - **Container Path**: `/app/data`
   - **Host Path**: (O Easypanel gerencia isso, apenas crie o volume).
6. Em **Network** (Portas):
   - Container Port: `8000`
   - Use o domínio interno do Easypanel ou deixe privado se possível (mas para o frontend acessar, geralmente precisa estar exposto ou na rede interna).
   - *Nota:* O frontend vai acessar pelo nome do serviço na rede interna Docker, mas se você quiser testar a API direto (Docs do Swagger), pode expor um domínio.
7. Clique em **Create** / **Deploy**.

## Passo 4: Criar o Serviço Frontend (Aplicação)

1. Crie outro **App** service chamado `frontend`.
2. Em **Source**:
   - Selecione o mesmo repositório do GitHub.
   - **Build Context**: Digite `/frontend`.
3. Em **Environment**:
   - Adicione:
     ```
     API_URL=http://backend:8000
     SECRET_KEY=crie-outra-senha-secreta
     FLASK_ENV=production
     ```
     *Nota:* `http://backend:8000` funciona porque o Easypanel coloca os serviços do mesmo projeto na mesma rede Docker e resolve pelo nome. Se não funcionar, verifique o nome exato do serviço backend criado.
4. Em **Network**:
   - Container Port: `5000`
   - **Domains**: Configure aqui seu domínio público (ex: `financeiro.seudominio.com`). O Easypanel cuidará do SSL (HTTPS) automaticamente.
5. Clique em **Create** / **Deploy**.

## Passo 5: Verificação

1. Acesse o domínio que você configurou para o Frontend.
2. Tente fazer Login/Cadastro.
3. Se houver erro, verifique os **Logs** dos serviços e se a variável `API_URL` do frontend está apontando corretamente para o backend.

---
**Dica:** Se o logo ou a página demorar para carregar, pode ser que o serviço esteja "Cold start". O Easypanel mantém rodando, então deve ser rápido.
