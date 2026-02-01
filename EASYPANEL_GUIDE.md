# Guia de Deploy no Easypanel

Sim, você deve criar **2 serviços** separados no Easypanel: um para o **Backend** e outro para o **Frontend**.

Aqui está o passo a passo para configurar cada um:

## 1. Criar o Projeto

1. No Easypanel, clique em **"Create Project"**.
2. Dê um nome, exemplo: `FinanceApp`.

## 2. Serviço 1: Backend (API + Banco de Dados)

1. Dentro do projeto, clique em **"Service"** > **"App"**.
2. Nome: `backend`.
3. **Source (Origem):**
   - Escolha **GitHub**.
   - Selecione seu repositório: `Leobmt02/FinanceApp`.
   - **Build Path (Caminho):** `/backend` (Importante: especifique a pasta!).
   - **DockerfilePath:** `Dockerfile` (padrão).
4. **Build (Construção):**
   - Port: `8000` (Porta que o FastAPI usa).
5. **Environment (Variáveis de Ambiente):**
   - Adicione as variáveis do `docker-compose.yml`:
     - `DATABASE_URL` = `sqlite:///./data/financeapp.db`
     - `SECRET_KEY` = (Crie uma senha forte)
     - `ALGORITHM` = `HS256`
     - `ACCESS_TOKEN_EXPIRE_MINUTES` = `60`
     - `FRONTEND_URL` = `https://financeapp-frontend.SEU_DOMINIO.com` (Substitua pelo domínio que o Easypanel criar para o frontend, ou use `*` para testar).
6. **Volumes (Persistência):**
   - Vá na aba **"Mounts"** (ou Volumes).
   - Adicione um volume:
     - Type: `Volume`
     - Name: `financeapp_data`
     - Mount Path: `/app/data` (Isso garante que o banco SQLite não suma ao reiniciar).
7. Clique em **"Deploy"**.

## 3. Serviço 2: Frontend

1. Crie outro serviço do tipo **"App"**.
2. Nome: `frontend`.
3. **Source (Origem):**
   - Mesmo repositório GitHub.
   - **Build Path:** `/frontend`.
4. **Build (Construção):**
   - Port: `5000` (Porta que o Flask usa).
5. **Environment (Variáveis de Ambiente):**
   - `API_URL` = `https://financeapp-backend.SEU_DOMINIO.com`
     - **Atenção:** Aqui você deve colocar a URL **pública** (HTTPS) que o Easypanel gerou para o seu serviço de Backend.
     - Diferente do Docker Compose local (que usa `http://backend:8000`), no Easypanel cada serviço tem seu domínio isolado.
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = (Uma senha segura para sessões).
6. Clique em **"Deploy"**.

## 4. Finalização

- Acesse a URL do **Frontend** gerada pelo Easypanel.
- Tente criar uma conta ou fazer login.
- Se houver erro de CORS ou conexão:
  - Verifique se a `API_URL` no Frontend está exatamente igual à URL do Backend (sem `/` no final, geralmente).
  - Verifique se a `FRONTEND_URL` no Backend corresponde à URL do Frontend.

## Resumo

| Configuração | Backend | Frontend |
| :--- | :--- | :--- |
| **Path** | `/backend` | `/frontend` |
| **Porta** | `8000` | `5000` |
| **Volume** | `/app/data` | Não precisa |
| **Variável Chave** | `DATABASE_URL` | `API_URL` |
