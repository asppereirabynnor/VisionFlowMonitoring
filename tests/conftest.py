import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import sys

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.base import Base, get_db
from main import app

# Cria um banco de dados em memória para os testes
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria as tabelas no banco de dados de teste
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db_session():
    """Fixture para criar uma sessão de banco de dados para os testes."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Fixture para criar um cliente de teste para a API."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    """Fixture para criar headers de autenticação para os testes."""
    # Em um ambiente real, você geraria um token JWT válido
    # Para testes, podemos usar um token fictício ou desabilitar a autenticação
    return {"Authorization": "Bearer test_token"}
