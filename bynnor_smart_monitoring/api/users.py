from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from db.base import get_db
from models.models import User, UserRole
from bynnor_smart_monitoring.auth.auth import (
    get_password_hash, 
    get_current_active_user, 
    get_admin_user,
    UserCreate,
    UserUpdate,
    UserResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["users"],
    responses={404: {"description": "Usuário não encontrado"}},
)

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Retorna a lista de usuários (apenas para administradores).
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna os detalhes de um usuário específico.
    Usuários normais só podem ver seus próprios dados.
    Administradores podem ver dados de qualquer usuário.
    """
    # Verifica permissões
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário com ID {user_id} não encontrado"
        )
    return user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Cria um novo usuário (apenas para administradores).
    """
    # Verifica se o usuário já existe
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já registrado"
        )
    
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
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        password=hashed_password,
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
        logger.error(f"Erro ao criar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {str(e)}"
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, 
    user_update: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza os dados de um usuário.
    Usuários normais só podem atualizar seus próprios dados e não podem alterar o papel.
    Administradores podem atualizar dados de qualquer usuário.
    """
    # Verifica permissões
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    
    # Usuários normais não podem alterar o papel
    if current_user.role != UserRole.ADMIN and user_update.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente para alterar o papel"
        )
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário com ID {user_id} não encontrado"
        )
    
    # Atualiza os campos fornecidos
    update_data = user_update.dict(exclude_unset=True)
    
    # Se a senha for fornecida, faz o hash
    if "password" in update_data:
        update_data["password"] = get_password_hash(update_data["password"])
    
    # Se o papel for fornecido, converte para enum
    if "role" in update_data:
        update_data["role"] = UserRole(update_data["role"])
    
    # Atualiza os campos no objeto do banco de dados
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar usuário: {str(e)}"
        )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Remove um usuário do sistema (apenas para administradores).
    """
    # Não permite excluir o próprio usuário
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir o próprio usuário"
        )
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário com ID {user_id} não encontrado"
        )
    
    try:
        db.delete(db_user)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir usuário: {str(e)}"
        )
