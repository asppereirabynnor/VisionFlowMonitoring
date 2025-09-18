from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from models.models import Base

# Cria o banco de dados SQLite
db_path = os.path.join(os.getcwd(), 'app.db')
engine = create_engine(f'sqlite:///{db_path}')

# Cria todas as tabelas
Base.metadata.create_all(engine)

print(f"Banco de dados inicializado em {db_path}")
