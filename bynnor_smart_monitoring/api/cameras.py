from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, Field
from enum import Enum
import time
from datetime import datetime

from db.base import get_db
from models.models import Camera, CameraStatus
from bynnor_smart_monitoring.core.camera import CameraManager

logger = logging.getLogger(__name__)

# Inicializa o gerenciador de câmeras
camera_manager = CameraManager()

router = APIRouter(
    tags=["cameras"],
    responses={404: {"description": "Câmera não encontrada"}},
)

# Modelos Pydantic para validação e serialização
class CameraStatusEnum(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    DISABLED = "disabled"

class CameraBase(BaseModel):
    name: str
    rtsp_url: str
    ip_address: str
    port: int = 554
    username: Optional[str] = None
    password: Optional[str] = None
    onvif_url: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    is_active: bool = True

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    onvif_url: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    is_active: Optional[bool] = None
    
class CameraScreenshotUpdate(BaseModel):
    screenshot_base64: str = Field(..., description="Imagem em formato base64 para simulação da câmera")

class CameraResponse(CameraBase):
    id: int
    status: CameraStatusEnum
    last_online: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    screenshot_base64: Optional[str] = None

    class Config:
        orm_mode = True

class CameraStats(BaseModel):
    id: int
    name: str
    status: CameraStatusEnum
    fps: float = 0.0
    resolution: str = ""
    uptime: float = 0.0
    event_count: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0

@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(camera: CameraCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Cria uma nova câmera no sistema.
    """
    try:
        # Cria o objeto Camera para o banco de dados
        db_camera = Camera(
            name=camera.name,
            rtsp_url=camera.rtsp_url,
            ip_address=camera.ip_address,
            port=camera.port,
            username=camera.username,
            password=camera.password,
            onvif_url=camera.onvif_url,
            description=camera.description,
            location=camera.location,
            model=camera.model,
            manufacturer=camera.manufacturer,
            is_active=camera.is_active,
            status=CameraStatus.OFFLINE
        )
        
        # Adiciona ao banco de dados
        db.add(db_camera)
        db.commit()
        db.refresh(db_camera)
        
        # Adiciona tarefa em background para conectar à câmera
        if camera.is_active:
            background_tasks.add_task(
                camera_manager.add_camera,
                str(db_camera.id),
                camera.name,
                camera.rtsp_url,
                camera.username,
                camera.password
            )
        
        return db_camera
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar câmera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar câmera: {str(e)}"
        )

@router.get("/", response_model=List[CameraResponse])
def get_cameras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retorna a lista de câmeras cadastradas.
    """
    cameras = db.query(Camera).offset(skip).limit(limit).all()
    return cameras

@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de uma câmera específica.
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    return camera

@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: int, 
    camera_update: CameraUpdate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Atualiza os dados de uma câmera.
    """
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if db_camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    # Atualiza os campos fornecidos
    update_data = camera_update.dict(exclude_unset=True)
    
    # Verifica se precisa reconectar a câmera
    reconnect = False
    if any(field in update_data for field in ['rtsp_url', 'username', 'password', 'is_active']):
        reconnect = True
        
        # Se a câmera estiver ativa no gerenciador, remove primeiro
        if str(camera_id) in camera_manager.cameras:
            camera_manager.remove_camera(str(camera_id))
    
    # Atualiza os campos no objeto do banco de dados
    for key, value in update_data.items():
        setattr(db_camera, key, value)
    
    try:
        db.commit()
        db.refresh(db_camera)
        
        # Reconecta a câmera se necessário
        if reconnect and db_camera.is_active:
            background_tasks.add_task(
                camera_manager.add_camera,
                str(db_camera.id),
                db_camera.name,
                db_camera.rtsp_url,
                db_camera.username,
                db_camera.password
            )
        
        return db_camera
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar câmera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar câmera: {str(e)}"
        )

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    """
    Remove uma câmera do sistema.
    """
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if db_camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    try:
        # Remove a câmera do gerenciador se estiver ativa
        if str(camera_id) in camera_manager.cameras:
            camera_manager.remove_camera(str(camera_id))
        
        # Remove do banco de dados
        db.delete(db_camera)
        db.commit()
        
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir câmera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir câmera: {str(e)}"
        )

@router.post("/{camera_id}/start", response_model=CameraResponse)
def start_camera(camera_id: int, db: Session = Depends(get_db)):
    """
    Inicia o streaming de uma câmera.
    """
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if db_camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    try:
        # Verifica se a câmera já está ativa
        if str(camera_id) in camera_manager.cameras:
            return db_camera
        
        # Inicia a câmera
        camera_manager.add_camera(
            str(db_camera.id),
            db_camera.name,
            db_camera.rtsp_url,
            db_camera.username,
            db_camera.password
        )
        
        # Atualiza o status no banco de dados
        db_camera.is_active = True
        db.commit()
        db.refresh(db_camera)
        
        return db_camera
    except Exception as e:
        logger.error(f"Erro ao iniciar câmera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar câmera: {str(e)}"
        )

@router.post("/{camera_id}/stop", response_model=CameraResponse)
def stop_camera(camera_id: int, db: Session = Depends(get_db)):
    """
    Para o streaming de uma câmera.
    """
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if db_camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    try:
        # Remove a câmera do gerenciador se estiver ativa
        if str(camera_id) in camera_manager.cameras:
            camera_manager.remove_camera(str(camera_id))
        
        # Atualiza o status no banco de dados
        db_camera.is_active = False
        db_camera.status = CameraStatus.DISABLED
        db.commit()
        db.refresh(db_camera)
        
        return db_camera
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao parar câmera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao parar câmera: {str(e)}"
        )

@router.get("/{camera_id}/stats", response_model=CameraStats)
def get_camera_stats(camera_id: int, db: Session = Depends(get_db)):
    """
    Retorna estatísticas de uma câmera.
    """
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if db_camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    # Obtém estatísticas do gerenciador de câmeras
    stats = {
        "id": db_camera.id,
        "name": db_camera.name,
        "status": db_camera.status.value,
        "fps": 0.0,
        "resolution": "",
        "uptime": 0.0,
        "event_count": 0,
        "cpu_usage": 0.0,
        "memory_usage": 0.0
    }
    
    # Se a câmera estiver ativa, obtém estatísticas em tempo real
    if str(camera_id) in camera_manager.cameras:
        camera = camera_manager.cameras[str(camera_id)]
        stats["fps"] = camera.get_fps()
        
        # Obtém a resolução
        frame = camera.get_latest_frame()
        if frame is not None:
            height, width = frame.shape[:2]
            stats["resolution"] = f"{width}x{height}"
        
        # Calcula o uptime
        if camera.start_time:
            stats["uptime"] = time.time() - camera.start_time
    
    return stats

@router.post("/{camera_id}/screenshot", response_model=CameraResponse)
def update_camera_screenshot(camera_id: int, screenshot: CameraScreenshotUpdate, db: Session = Depends(get_db)):
    """
    Atualiza o screenshot de uma câmera para simulação.
    """
    logger.info(f"Recebendo requisição para atualizar screenshot da câmera ID {camera_id}")
    
    # Verificar se a câmera existe
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if db_camera is None:
        logger.error(f"Câmera com ID {camera_id} não encontrada")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    logger.info(f"Câmera encontrada: {db_camera.name}")
    
    # Verificar se o screenshot foi recebido corretamente
    if not screenshot or not screenshot.screenshot_base64:
        logger.error("Screenshot base64 não fornecido ou inválido")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Screenshot base64 não fornecido ou inválido"
        )
    
    # Verificar o tamanho do screenshot
    screenshot_size = len(screenshot.screenshot_base64)
    logger.info(f"Tamanho do screenshot recebido: {screenshot_size} caracteres")
    
    try:
        # Atualiza o screenshot da câmera
        logger.info("Atualizando screenshot no banco de dados...")
        db_camera.screenshot_base64 = screenshot.screenshot_base64
        db.commit()
        db.refresh(db_camera)
        
        logger.info("Screenshot atualizado com sucesso!")
        return db_camera
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar screenshot da câmera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar screenshot da câmera: {str(e)}"
        )
