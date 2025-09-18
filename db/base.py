from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Obter a URL do banco de dados das variáveis de ambiente ou usar um valor padrão
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/bynnor.db")

# Garantir que o diretório data existe
db_path = os.path.dirname(SQLALCHEMY_DATABASE_URL.replace("sqlite:///", ""))
if db_path and not os.path.exists(db_path):
    os.makedirs(db_path, exist_ok=True)

# Configurar o engine do SQLAlchemy
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
