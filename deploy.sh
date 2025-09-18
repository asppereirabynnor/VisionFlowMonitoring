#!/bin/bash
set -e

# Cores para saída
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando implantação do Bynnor Smart Monitoring...${NC}"

# Verificar se o Docker está em execução
if ! docker info > /dev/null 2>&1; then
  echo "Erro: Docker não está em execução. Por favor, inicie o Docker e tente novamente."
  exit 1
fi

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
  echo -e "${YELLOW}Arquivo .env não encontrado. Criando um arquivo .env padrão...${NC}"
  cat > .env << EOL
JWT_SECRET=bynnor_secret_key_change_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EOL
  echo -e "${GREEN}Arquivo .env criado. Por favor, edite-o com suas configurações.${NC}"
fi

# Puxar as imagens mais recentes do Docker Hub
echo -e "${YELLOW}Baixando as imagens mais recentes do Docker Hub...${NC}"
docker-compose pull

# Iniciar os serviços
echo -e "${YELLOW}Iniciando os serviços...${NC}"
docker-compose up -d

# Verificar se os serviços estão em execução
echo -e "${YELLOW}Verificando o status dos serviços...${NC}"
docker-compose ps

echo -e "${GREEN}Implantação concluída com sucesso!${NC}"
echo -e "${GREEN}Frontend disponível em: http://localhost${NC}"
echo -e "${GREEN}Backend disponível em: http://localhost:8000${NC}"
echo -e "${YELLOW}Para visualizar os logs, execute: docker-compose logs -f${NC}"
