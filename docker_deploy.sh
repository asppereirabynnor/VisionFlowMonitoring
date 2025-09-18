#!/bin/bash
set -e

# Cores para saída
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== VisionFlow Monitoring - Implantação Docker ===${NC}"

# Verificar se o Docker está em execução
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Erro: Docker não está em execução. Por favor, inicie o Docker e tente novamente.${NC}"
  exit 1
fi

# Verificar login no Docker Hub
echo -e "${YELLOW}Verificando login no Docker Hub...${NC}"
if ! docker info | grep -q "Username"; then
  echo -e "${YELLOW}Fazendo login no Docker Hub...${NC}"
  docker login
fi

# Construir as imagens
echo -e "${YELLOW}Construindo imagens Docker...${NC}"
docker-compose build

# Verificar se a construção foi bem-sucedida
if [ $? -ne 0 ]; then
  echo -e "${RED}Erro: Falha na construção das imagens Docker.${NC}"
  exit 1
fi

# Publicar as imagens no Docker Hub
echo -e "${YELLOW}Publicando imagens no Docker Hub...${NC}"

echo -e "${GREEN}Publicando backend...${NC}"
docker push asppereira/bynnor-vision:backend

echo -e "${GREEN}Publicando frontend...${NC}"
docker push asppereira/bynnor-vision:frontend

echo -e "${GREEN}Publicação concluída com sucesso!${NC}"

# Opção para implantar localmente
read -p "Deseja iniciar os serviços localmente? (s/n): " start_locally
if [[ $start_locally == "s" || $start_locally == "S" ]]; then
  echo -e "${YELLOW}Iniciando serviços localmente...${NC}"
  docker-compose up -d
  
  echo -e "${GREEN}Serviços iniciados com sucesso!${NC}"
  echo -e "${GREEN}Frontend disponível em: http://localhost${NC}"
  echo -e "${GREEN}Backend disponível em: http://localhost:8000${NC}"
  echo -e "${GREEN}Documentação da API: http://localhost:8000/docs${NC}"
  
  echo -e "${YELLOW}Para visualizar os logs, execute: docker-compose logs -f${NC}"
fi

exit 0
