# Guia de Deploy - FinanceApp na VPS Contabo

Este guia orienta como subir o FinanceApp (Frontend + Backend) em sua VPS usando Docker.

## Pré-requisitos na VPS

1. **Acesso SSH** à sua VPS.
2. **Git** (opcional, para clonar se usar repo) ou **Upload de arquivos** (via SFTP/SCP).
3. **Docker** e **Docker Compose** instalados.

### Instalar Docker (se não tiver)
Em VPS Ubuntu/Debian:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# (Faça logout e login novamente para aplicar permissões de grupo)
```

## Passo a Passo do Deploy

1. **Upload dos Arquivos**
   Copie todo o conteúdo da pasta `financeapp` (extraída do ZIP) para uma pasta na VPS, por exemplo `~/financeapp`.
   
   Certifique-se de que os seguintes arquivos estejam presentes:
   - `docker-compose.yml`
   - Pasta `backend/` (com `Dockerfile`, `requirements.txt`, e código `app/`)
   - Pasta `frontend/` (com `Dockerfile`, `requirements.txt` e código)

2. **Configuração de Ambiente**
   Edite o `docker-compose.yml` se quiser alterar senhas ou portas:
   - `SECRET_KEY`: altere para uma string aleatória segura.
   - As portas padrão são `80:5000` (Frontend acessível na porta 80) e `8001:8000` (Backend acessível externamente na 8001).
   - O Frontend se comunica com o Backend internamente, então essa porta externa 8001 é apenas para acesso direto à API/Docs se necessário.
   - Se já tiver outro serviço na porta 80, altere `"80:5000"` para `"5001:5000"` ou similar.

3. **Subir os Containers**
   Na pasta do projeto, execute:
   ```bash
   docker compose up -d --build
   ```
   
   Isso irá:
   - Construir as imagens do frontend e backend.
   - Baixar dependências.
   - Iniciar os serviços em segundo plano (-d).

4. **Verificar Status**
   ```bash
   docker compose ps
   ```
   Você deve ver `financeapp-backend` e `financeapp-frontend` como `Up`.

5. **Acesso**
   Abra seu navegador e acesse o IP da sua VPS:
   `http://SEU_IP_VPS` (ou `http://SEU_IP_VPS:5000` se removeu o redirecionamento da porta 80).

## Manutenção e Dados

- **Dados do Banco:** O banco de dados SQLite é salvo em `./financeapp_data/financeapp.db` na VPS (mapeado pelo docker-compose). Esse arquivo persiste mesmo se reiniciar os containers.
- **Logs:** Para ver erros ou logs de acesso:
  ```bash
  docker compose logs -f
  ```
- **Parar:**
  ```bash
  docker compose down
  ```
- **Atualizar:** Se alterar código, rode `docker compose up -d --build` novamente.
