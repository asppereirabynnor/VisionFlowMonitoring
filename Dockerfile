FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Cria diretórios para dados persistentes
RUN mkdir -p /app/data /app/uploads /app/events

# Configura variáveis de ambiente para SQLite
ENV DATABASE_URL=sqlite:///./data/bynnor.db
ENV SQLITE_DB=/app/data/bynnor.db

# Copia os arquivos de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o script de entrypoint e torna-o executável
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Copia o código da aplicação
COPY . .

# Expõe a porta da aplicação
EXPOSE 8000

# Define o script de inicialização como entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Comando para executar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
