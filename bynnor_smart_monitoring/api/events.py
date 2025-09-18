from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel
from datetime import datetime
import os
import json
from pathlib import Path

from db.base import get_db
from models.models import Event, EventType, Camera
from bynnor_smart_monitoring.core.recording import EventManager

logger = logging.getLogger(__name__)

# Inicializa o gerenciador de eventos
event_manager = EventManager()

router = APIRouter(
    tags=["events"],
    responses={404: {"description": "Evento não encontrado"}},
)

# Modelos Pydantic para validação e serialização
class EventBase(BaseModel):
    type: str
    description: Optional[str] = None
    camera_id: int
    confidence: Optional[int] = None  # 0-100 no banco de dados

class EventCreate(EventBase):
    metadata: Optional[Dict[str, Any]] = None

class EventResponse(BaseModel):
    id: int
    type: str
    description: Optional[str] = None
    confidence: Optional[int] = None
    event_metadata: Optional[str] = None  # JSON string no banco de dados
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    created_at: datetime
    camera_id: int
    created_by_id: Optional[int] = None
    
    class Config:
        orm_mode = True
        arbitrary_types_allowed = True

class EventFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    camera_id: Optional[int] = None
    event_type: Optional[str] = None
    min_confidence: Optional[float] = None

# IMPORTANTE: Rotas específicas primeiro, antes das rotas com parâmetros
@router.get("/types", response_model=List[str])
def get_event_types():
    """
    Retorna todos os tipos de eventos disponíveis.
    """
    # Retorna diretamente os valores do enum sem precisar de acesso ao banco de dados
    return ["motion", "person", "vehicle", "object", "alert", "system"]

@router.get("/stats", response_model=dict)
@router.get("/stats/summary", response_model=dict)
def get_events_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    camera_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna um resumo estatístico dos eventos.
    """
    try:
        # Base query
        query = db.query(Event)
        
        # Aplica filtros
        if start_date:
            query = query.filter(Event.created_at >= start_date)
        
        if end_date:
            query = query.filter(Event.created_at <= end_date)
        
        if camera_id:
            query = query.filter(Event.camera_id == camera_id)
        
        # Conta total de eventos
        total_events = query.count()
        
        # Conta eventos por tipo
        events_by_type = {}
        for event_type in EventType:
            count = query.filter(Event.type == event_type).count()
            events_by_type[event_type.value] = count
        
        # Conta eventos por câmera
        events_by_camera = {}
        if not camera_id:  # Só faz sentido se não estiver filtrando por câmera
            cameras = db.query(Camera).all()
            for camera in cameras:
                count = query.filter(Event.camera_id == camera.id).count()
                events_by_camera[camera.name] = count
        
        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_camera": events_by_camera
        }
    except Exception as e:
        logger.error(f"Erro ao obter resumo de eventos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter resumo de eventos: {str(e)}"
        )

@router.get("/", response_model=List[EventResponse])
def get_events(
    skip: int = 0, 
    limit: int = 100,
    camera_id: Optional[int] = None,
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de eventos com filtros opcionais.
    """
    query = db.query(Event)
    
    # Aplica os filtros
    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    
    if event_type:
        query = query.filter(Event.type == event_type)
    
    if start_date:
        query = query.filter(Event.created_at >= start_date)
    
    if end_date:
        query = query.filter(Event.created_at <= end_date)
    
    if min_confidence:
        query = query.filter(Event.confidence >= min_confidence * 100)  # Converte para percentual
    
    # Ordena por data (mais recentes primeiro)
    query = query.order_by(Event.created_at.desc())
    
    # Aplica paginação
    events = query.offset(skip).limit(limit).all()
    
    return events

@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """
    Cria um novo evento manualmente.
    """
    # Verifica se a câmera existe
    camera = db.query(Camera).filter(Camera.id == event.camera_id).first()
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {event.camera_id} não encontrada"
        )
    
    try:
        # Cria o objeto Event para o banco de dados
        db_event = Event(
            type=EventType(event.type),
            description=event.description,
            camera_id=event.camera_id,
            confidence=event.confidence,  # Já está na escala 0-100
            event_metadata=json.dumps(event.metadata) if event.metadata else None
        )
        
        # Adiciona ao banco de dados
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        return db_event
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar evento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar evento: {str(e)}"
        )

# IMPORTANTE: Rotas com parâmetros depois das rotas específicas
@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um evento específico.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evento com ID {event_id} não encontrado"
        )
    return event

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """
    Remove um evento do sistema.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evento com ID {event_id} não encontrado"
        )
    
    try:
        # Remove arquivos associados se existirem
        if event.image_path and os.path.exists(event.image_path):
            os.remove(event.image_path)
            
        if event.video_path and os.path.exists(event.video_path):
            os.remove(event.video_path)
        
        # Remove do banco de dados
        db.delete(event)
        db.commit()
        
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir evento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir evento: {str(e)}"
        )

@router.get("/{event_id}/video", response_class=Response)
def get_event_video(event_id: int, db: Session = Depends(get_db)):
    """
    Retorna o vídeo de um evento.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evento com ID {event_id} não encontrado"
        )
    
    if not event.video_path or not os.path.exists(event.video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vídeo não encontrado para o evento {event_id}"
        )
    
    try:
        # Lê o arquivo de vídeo
        with open(event.video_path, "rb") as video_file:
            video_data = video_file.read()
        
        # Retorna o vídeo
        return Response(
            content=video_data,
            media_type="video/mp4"
        )
    except Exception as e:
        logger.error(f"Erro ao obter vídeo do evento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter vídeo do evento: {str(e)}"
        )

@router.get("/{event_id}/image", response_class=Response)
def get_event_image(event_id: int, db: Session = Depends(get_db)):
    """
    Retorna a imagem de um evento.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evento com ID {event_id} não encontrado"
        )
    
    if not event.image_path or not os.path.exists(event.image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Imagem não encontrada para o evento {event_id}"
        )
    
    try:
        # Lê o arquivo de imagem
        with open(event.image_path, "rb") as image_file:
            image_data = image_file.read()
        
        # Determina o tipo de mídia com base na extensão
        extension = Path(event.image_path).suffix.lower()
        media_type = "image/jpeg"  # Padrão
        
        if extension == ".png":
            media_type = "image/png"
        elif extension == ".gif":
            media_type = "image/gif"
        
        # Retorna a imagem
        return Response(
            content=image_data,
            media_type=media_type
        )
    except Exception as e:
        logger.error(f"Erro ao obter imagem do evento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter imagem do evento: {str(e)}"
        )
