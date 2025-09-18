#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Importar os modelos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.models import User, UserRole, Base

# Configuração de criptografia
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_user(username, email, password, role="admin", full_name=None):
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Configuração do banco de dados para SQLite
    SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
    
    # Criar conexão com o banco de dados
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Verificar se o usuário já existe
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Usuário com email {email} já existe!")
            return False
        
        # Criar o usuário
        hashed_password = get_password_hash(password)
        user_role = UserRole(role)
        
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=user_role,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"Usuário {email} criado com sucesso!")
        return True
    
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar usuário: {e}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python create_user.py <username> <email> <senha> [role] [nome_completo]")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    role = sys.argv[4] if len(sys.argv) > 4 else "admin"
    full_name = sys.argv[5] if len(sys.argv) > 5 else None
    
    create_user(username, email, password, role, full_name)
