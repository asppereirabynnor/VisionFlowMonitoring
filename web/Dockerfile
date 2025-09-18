FROM node:18-alpine as build

WORKDIR /app

# Copiar arquivos de dependências
COPY package.json package-lock.json* ./

# Instalar dependências
RUN npm ci

# Copiar código fonte
COPY . .

# Definir variáveis de ambiente para build
ARG REACT_APP_API_URL=http://localhost:8000
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

# Construir o aplicativo
RUN npm run build

# Estágio de produção
FROM nginx:alpine

# Copiar arquivos de build para o nginx
COPY --from=build /app/build /usr/share/nginx/html

# Copiar configuração personalizada do nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expor porta 80
EXPOSE 80

# Comando para iniciar o nginx
CMD ["nginx", "-g", "daemon off;"]
