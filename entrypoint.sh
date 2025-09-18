#!/bin/bash
set -e

# Verifica se o diretório de dados existe
if [ ! -d "/app/data" ]; then
  mkdir -p /app/data
fi

# Verifica se o banco SQLite já existe
if [ ! -f "$SQLITE_DB" ]; then
  echo "Criando banco de dados SQLite..."
  touch "$SQLITE_DB"
  echo "Banco SQLite criado em $SQLITE_DB"
fi

# Executa as migrações do Alembic
echo "Aplicando migrações do banco de dados..."
alembic upgrade head

# Cria diretórios para uploads e eventos se não existirem
if [ ! -d "/app/uploads" ]; then
  mkdir -p /app/uploads
fi

if [ ! -d "/app/events" ]; then
  mkdir -p /app/events
fi

# Ajusta permissões
chmod -R 777 /app/data /app/uploads /app/events

# Inicia a aplicação
echo "Iniciando a aplicação..."
exec "$@"
