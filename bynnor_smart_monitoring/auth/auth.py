from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
import os
import logging
from dotenv import load_dotenv

from db.base import get_db
from models.models import User, UserRole

# Carrega variáveis de ambiente
load_dotenv()

# Configurações de segurança
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-secret-key-for-development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

logger = logging.getLogger(__name__)

# Configuração do router
router = APIRouter(
    tags=["auth"],
)

# Configuração de segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Modelos Pydantic
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: str = "USER"
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Funções de segurança
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    # Usa o email em vez de username
    user = db.query(User).filter(User.email == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    return current_user

def verify_token(token: str):
    """
    Verifica se o token JWT é válido e retorna o payload
    """
    try:
        # Decodificar o token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Token verificado com sucesso: {token[:10]}...")
        return payload
    except JWTError as e:
        logger.error(f"Erro ao verificar token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado na verificação do token: {str(e)}")
        return None

async def verify_token_websocket(token: str, db: Session) -> User:
    """
    Verifica se o token JWT é válido para conexões WebSocket
    """
    logger.info(f"Verificando token WebSocket: {token[:20]}...")
    
    try:
        # Decodificar o token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Payload decodificado: {payload}")
        
        # Extrair o email (subject) do payload
        email: str = payload.get("sub")
        if email is None:
            logger.error("Token não contém campo 'sub'")
            return None
            
        # Buscar o usuário no banco de dados
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            logger.error(f"Usuário com email {email} não encontrado")
            return None
            
        if not user.is_active:
            logger.error(f"Usuário {email} está inativo")
            return None
            
        logger.info(f"Usuário {email} autenticado com sucesso via WebSocket")
        return user
        
    except JWTError as e:
        logger.error(f"Erro ao decodificar token JWT: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado na verificação do token: {str(e)}")
        return None

def get_user_from_token(token: str, db: Session) -> User:
    """
    Extrai e retorna o usuário a partir de um token JWT
    
    Args:
        token: Token JWT (sem o prefixo 'Bearer')
        db: Sessão do banco de dados
        
    Returns:
        User: Objeto do usuário se o token for válido, None caso contrário
    """
    try:
        # Remover prefixo 'Bearer' se presente
        if token.startswith("Bearer "):
            token = token[7:]
            
        # Decodificar o token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extrair o email (subject) do payload
        email: str = payload.get("sub")
        if email is None:
            logger.error("Token não contém campo 'sub'")
            return None
            
        # Buscar o usuário no banco de dados
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            logger.error(f"Usuário com email {email} não encontrado")
            return None
            
        if not user.is_active:
            logger.error(f"Usuário {email} está inativo")
            return None
            
        return user
        
    except JWTError as e:
        logger.error(f"Erro ao decodificar token JWT: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado na verificação do token: {str(e)}")
        return None

# Rotas de autenticação
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value, "user_id": user.id},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    }

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Verifica se o email já existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )
    
    # Cria o novo usuário
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=UserRole(user.role),
        is_active=user.is_active
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao registrar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar usuário: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user
