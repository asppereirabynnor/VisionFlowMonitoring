# Guia de Implantação - Bynnor Smart Monitoring

Este documento descreve o processo de implantação do sistema Bynnor Smart Monitoring usando Docker e Docker Compose.

## Pré-requisitos

- Docker instalado e em execução
- Docker Compose instalado
- Conta no Docker Hub (para publicação das imagens)

## Estrutura do Projeto

O projeto está organizado da seguinte forma:

- **Backend**: API FastAPI com SQLite
- **Frontend**: Aplicação React
- **Banco de Dados**: SQLite (persistido em volume Docker)

## Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```
JWT_SECRET=seu_segredo_jwt_aqui
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

## Construção e Execução Local

Para construir e executar o projeto localmente:

```bash
# Construir as imagens
docker-compose build

# Iniciar os serviços
docker-compose up -d

# Verificar logs
docker-compose logs -f
```

O frontend estará disponível em `http://localhost` e o backend em `http://localhost:8000`.

## Publicação no Docker Hub

Para publicar as imagens no Docker Hub, você pode usar o script fornecido:

```bash
# Tornar o script executável (se ainda não estiver)
chmod +x publish_to_dockerhub.sh

# Executar o script
./publish_to_dockerhub.sh
```

Ou manualmente:

```bash
# Fazer login no Docker Hub
docker login

# Construir as imagens
docker-compose build

# Publicar as imagens
docker push asppereira/bynnor-vision:backend
docker push asppereira/bynnor-vision:frontend
```

## Implantação em Produção

Para implantar em um servidor de produção:

1. Clone o repositório ou copie os arquivos `docker-compose.yml` e `.env`
2. Configure as variáveis de ambiente no arquivo `.env`
3. Execute:

```bash
docker-compose pull
docker-compose up -d
```

## Volumes e Persistência de Dados

Os seguintes volumes são usados para persistência de dados:

- `sqlite_data`: Armazena o banco de dados SQLite
- `uploads_data`: Armazena os arquivos enviados
- `events_data`: Armazena os eventos gerados

## Manutenção

### Backup do Banco de Dados

Para fazer backup do banco de dados SQLite:

```bash
docker-compose exec backend sh -c "sqlite3 /app/data/bynnor.db .dump > /app/data/backup.sql"
docker cp bynnor_backend:/app/data/backup.sql ./backup.sql
```

### Restauração do Banco de Dados

Para restaurar o banco de dados a partir de um backup:

```bash
docker cp ./backup.sql bynnor_backend:/app/data/backup.sql
docker-compose exec backend sh -c "cat /app/data/backup.sql | sqlite3 /app/data/bynnor.db"
```

### Atualização

Para atualizar para uma nova versão:

```bash
# Parar os serviços
docker-compose down

# Puxar as novas imagens
docker-compose pull

# Iniciar os serviços novamente
docker-compose up -d
```

## Solução de Problemas

### Verificar Logs

```bash
# Todos os serviços
docker-compose logs -f

# Apenas backend
docker-compose logs -f backend

# Apenas frontend
docker-compose logs -f frontend
```

### Reiniciar Serviços

```bash
# Reiniciar todos os serviços
docker-compose restart

# Reiniciar apenas o backend
docker-compose restart backend

# Reiniciar apenas o frontend
docker-compose restart frontend
```
