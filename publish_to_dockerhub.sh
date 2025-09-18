#!/bin/bash
set -e

# Cores para saída
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando processo de publicação no Docker Hub...${NC}"

# Verificar se o Docker está em execução
if ! docker info > /dev/null 2>&1; then
  echo "Erro: Docker não está em execução. Por favor, inicie o Docker e tente novamente."
  exit 1
fi

# Verificar login no Docker Hub
echo -e "${YELLOW}Verificando login no Docker Hub...${NC}"
if ! docker info | grep -q "Username"; then
  echo "Fazendo login no Docker Hub..."
  docker login
fi

# Construir as imagens
echo -e "${YELLOW}Construindo imagens Docker...${NC}"
docker-compose build

# Publicar as imagens no Docker Hub
echo -e "${YELLOW}Publicando imagens no Docker Hub...${NC}"
echo -e "${GREEN}Publicando backend...${NC}"
docker push asppereira/bynnor-vision:backend

echo -e "${GREEN}Publicando frontend...${NC}"
docker push asppereira/bynnor-vision:frontend

echo -e "${GREEN}Publicação concluída com sucesso!${NC}"
