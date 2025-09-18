from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path do Python
sys.path.append(os.getcwd())

# Carrega as variáveis de ambiente
load_dotenv()

# Importa os modelos para que o Alembic possa detectar as alterações
from models.models import Base

# Configuração do Alembic
config = context.config

# Configura a URL do banco de dados para SQLite
sqlalchemy_url = f"sqlite:///{os.path.join(os.getcwd(), 'app.db')}"
config.set_main_option('sqlalchemy.url', sqlalchemy_url)

# Configura o logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Executa migrações no modo 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Executa migrações no modo 'online'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
