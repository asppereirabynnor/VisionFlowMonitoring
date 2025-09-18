from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, Field
import time
from datetime import datetime
from urllib.parse import urlparse

from db.base import get_db
from models.models import Camera, CameraPreset
from bynnor_smart_monitoring.core.onvif import ONVIFController, ONVIFConfig, PTZPosition
from bynnor_smart_monitoring.auth.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["onvif"],
    responses={404: {"description": "Câmera não encontrada"}},
)

# Modelos Pydantic para validação e serialização
class PTZCommand(BaseModel):
    pan: Optional[float] = Field(None, description="Movimento horizontal (-1.0 a 1.0)")
    tilt: Optional[float] = Field(None, description="Movimento vertical (-1.0 a 1.0)")
    zoom: Optional[float] = Field(None, description="Zoom (-1.0 a 1.0)")
    speed: Optional[float] = Field(0.5, description="Velocidade do movimento (0.1 a 1.0)")
    continuous: bool = Field(False, description="Se verdadeiro, movimento contínuo")
    stop: bool = Field(False, description="Se verdadeiro, para o movimento")

class PresetBase(BaseModel):
    name: str
    description: Optional[str] = None

class PresetCreate(PresetBase):
    pass

class PresetResponse(PresetBase):
    id: int
    camera_id: int
    preset_token: str
    created_at: datetime

    class Config:
        orm_mode = True

class DeviceInfo(BaseModel):
    manufacturer: str
    model: str
    firmware_version: str
    serial_number: str
    hardware_id: str

class ONVIFCapabilities(BaseModel):
    ptz: bool = False
    imaging: bool = False
    media: bool = False
    events: bool = False
    analytics: bool = False

class RTSPChannel(BaseModel):
    token: str
    name: str
    rtsp_url: Optional[str] = None
    resolution: Optional[str] = None
    encoding: Optional[str] = None
    framerate: Optional[float] = None
    bitrate: Optional[int] = None

# Função auxiliar para obter o controlador ONVIF para uma câmera
def get_onvif_controller(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    if not camera.onvif_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Câmera com ID {camera_id} não tem URL ONVIF configurada"
        )
    
    try:
        # Extrair IP e porta da URL ONVIF usando urllib.parse para maior robustez
        parsed_url = urlparse(camera.onvif_url)
        
        # Verificar se a URL está em formato válido
        if not parsed_url.netloc and not parsed_url.hostname:
            # Se a URL não tem formato válido (ex: apenas um IP sem http://), tentar corrigir
            if '://' not in camera.onvif_url:
                fixed_url = f"http://{camera.onvif_url}"
                logger.warning(f"URL ONVIF mal formatada: {camera.onvif_url}, tentando corrigir para {fixed_url}")
                parsed_url = urlparse(fixed_url)
        
        # Extrair IP e porta
        ip = parsed_url.hostname
        if not ip:
            # Tentar extrair manualmente se ainda for None
            parts = camera.onvif_url.split('/')
            for part in parts:
                if part and '.' in part and not part.startswith('http'):
                    ip_parts = part.split(':')[0]
                    if all(p.isdigit() or p == '.' for p in ip_parts):
                        ip = ip_parts
                        break
            
            if not ip:
                # Último recurso: usar o IP da câmera do banco de dados
                ip = camera.ip_address
                logger.warning(f"Não foi possível extrair IP da URL ONVIF, usando IP do banco de dados: {ip}")
        
        # Extrair porta
        port = parsed_url.port
        if not port:
            # Tentar extrair manualmente
            for part in camera.onvif_url.split('/'):
                if ':' in part and not part.startswith('http'):
                    try:
                        port = int(part.split(':')[1])
                        break
                    except (IndexError, ValueError):
                        pass
            
            # Se ainda não tiver porta, usar a padrão
            if not port:
                port = 80
                logger.info(f"Porta não especificada na URL ONVIF, usando porta padrão: {port}")
        
        logger.info(f"Conectando à câmera ONVIF: {ip}:{port} (URL: {camera.onvif_url})")
        
        # Validar IP
        if not ip:
            raise ValueError(f"Não foi possível extrair um IP válido da URL: {camera.onvif_url}")
        
        # Garantir que a porta seja um inteiro
        try:
            port = int(port)
        except (ValueError, TypeError):
            logger.warning(f"Porta inválida: {port}, usando porta padrão 80")
            port = 80
            
        # Garantir que credenciais sejam strings
        username = str(camera.username) if camera.username else ""
        password = str(camera.password) if camera.password else ""
        
        logger.info(f"Criando configuração ONVIF com IP={ip}, Porta={port}")
        
        config = ONVIFConfig(
            ip=ip,
            port=port,
            username=username,
            password=password
        )
        
        controller = ONVIFController(config)
        if not controller.connect():
            raise Exception("Falha ao conectar à câmera via ONVIF")
            
        return controller
    except Exception as e:
        logger.error(f"Erro ao conectar ao serviço ONVIF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao conectar ao serviço ONVIF: {str(e)}"
        )

@router.post("/cameras/{camera_id}/ptz", status_code=status.HTTP_200_OK)
def control_ptz(
    camera_id: int,
    command: PTZCommand,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Controla os movimentos PTZ (Pan, Tilt, Zoom) de uma câmera.
    """
    controller = get_onvif_controller(camera_id, db)
    
    try:
        if command.stop:
            # Para o movimento
            controller.stop_movement()
            return {"message": "Movimento PTZ parado com sucesso"}
        
        if command.continuous:
            # Movimento contínuo
            pan_speed = command.pan if command.pan is not None else 0.0
            tilt_speed = command.tilt if command.tilt is not None else 0.0
            zoom_speed = command.zoom if command.zoom is not None else 0.0
            
            controller.move_continuous(
                pan_speed=pan_speed,
                tilt_speed=tilt_speed,
                zoom_speed=zoom_speed
            )
            return {"message": "Movimento contínuo iniciado com sucesso"}
        else:
            # Obter posição atual
            current_position = controller.get_ptz_position()
            if not current_position:
                raise Exception("Não foi possível obter a posição atual da câmera")
                
            # Calcular nova posição relativa
            new_position = PTZPosition(
                pan=current_position.pan + (command.pan or 0.0),
                tilt=current_position.tilt + (command.tilt or 0.0),
                zoom=current_position.zoom + (command.zoom or 0.0)
            )
            
            # Mover para a nova posição
            controller.move_absolute(new_position)
            return {"message": "Movimento relativo executado com sucesso"}
    
    except Exception as e:
        logger.error(f"Erro ao controlar PTZ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao controlar PTZ: {str(e)}"
        )

@router.get("/cameras/{camera_id}/presets", response_model=List[PresetResponse])
def get_presets(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Retorna a lista de presets configurados para uma câmera.
    """
    # Verifica se a câmera existe
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    # Obtém os presets do banco de dados
    presets = db.query(CameraPreset).filter(CameraPreset.camera_id == camera_id).all()
    
    return presets

@router.post("/cameras/{camera_id}/presets", response_model=PresetResponse, status_code=status.HTTP_201_CREATED)
def create_preset(
    camera_id: int,
    preset: PresetCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Cria um novo preset com a posição atual da câmera.
    """
    # Verifica se a câmera existe
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    # Obtém o controlador ONVIF
    controller = get_onvif_controller(camera_id, db)
    
    try:
        # Cria o preset na câmera
        preset_token = controller.set_preset(preset.name)
        if not preset_token:
            raise Exception("Falha ao criar preset na câmera")
        
        # Cria o registro no banco de dados
        db_preset = CameraPreset(
            name=preset.name,
            description=preset.description,
            camera_id=camera_id,
            preset_token=preset_token
        )
        
        db.add(db_preset)
        db.commit()
        db.refresh(db_preset)
        
        return db_preset
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar preset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar preset: {str(e)}"
        )

@router.post("/cameras/{camera_id}/presets/{preset_id}/goto", status_code=status.HTTP_200_OK)
def goto_preset(
    camera_id: int,
    preset_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Move a câmera para um preset específico.
    """
    # Verifica se o preset existe
    preset = db.query(CameraPreset).filter(
        CameraPreset.id == preset_id,
        CameraPreset.camera_id == camera_id
    ).first()
    
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset com ID {preset_id} não encontrado para a câmera {camera_id}"
        )
    
    # Obtém o controlador ONVIF
    controller = get_onvif_controller(camera_id, db)
    
    try:
        # Move para o preset
        success = controller.go_to_preset(preset.preset_token)
        if not success:
            raise Exception("Falha ao mover para o preset")
        
        return {"message": f"Câmera movida para o preset '{preset.name}'"}
    
    except Exception as e:
        logger.error(f"Erro ao mover para preset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao mover para preset: {str(e)}"
        )

@router.delete("/cameras/{camera_id}/presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(
    camera_id: int,
    preset_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Remove um preset da câmera.
    """
    # Verifica se o preset existe
    preset = db.query(CameraPreset).filter(
        CameraPreset.id == preset_id,
        CameraPreset.camera_id == camera_id
    ).first()
    
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset com ID {preset_id} não encontrado para a câmera {camera_id}"
        )
    
    # Obtém o controlador ONVIF
    controller = get_onvif_controller(camera_id, db)
    
    try:
        # Remove o preset da câmera
        controller.remove_preset(preset.preset_token)
        
        # Remove do banco de dados
        db.delete(preset)
        db.commit()
        
        return None
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao remover preset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover preset: {str(e)}"
        )

@router.get("/cameras/{camera_id}/info", response_model=DeviceInfo)
def get_device_info(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Obtém informações do dispositivo da câmera.
    """
    try:
        controller = get_onvif_controller(camera_id, db)
        
        # Obtém informações do dispositivo
        device_info = controller.get_device_info()
        
        # Garantir que device_info é um dicionário válido
        if not isinstance(device_info, dict):
            logger.warning(f"get_device_info retornou um tipo inválido: {type(device_info)}")
            device_info = {}
        
        # Criar resposta com valores padrão para campos ausentes
        return DeviceInfo(
            manufacturer=device_info.get("Manufacturer", "Desconhecido"),
            model=device_info.get("Model", "Desconhecido"),
            firmware_version=device_info.get("FirmwareVersion", "Desconhecido"),
            serial_number=device_info.get("SerialNumber", "Desconhecido"),
            hardware_id=device_info.get("HardwareId", "Desconhecido")
        )
    
    except Exception as e:
        logger.error(f"Erro ao obter informações do dispositivo: {e}")
        
        # Retornar informações padrão em vez de falhar
        return DeviceInfo(
            manufacturer="Desconhecido (Erro de conexão)",
            model="Desconhecido",
            firmware_version="Desconhecido",
            serial_number="Desconhecido",
            hardware_id="Desconhecido"
        )

@router.get("/cameras/{camera_id}/capabilities", response_model=ONVIFCapabilities)
def get_capabilities(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Obtém as capacidades ONVIF da câmera.
    """
    controller = get_onvif_controller(camera_id, db)
    
    try:
        # Obtém capacidades
        capabilities = controller.get_capabilities()
        
        return ONVIFCapabilities(
            ptz=capabilities.get("ptz", False),
            imaging=capabilities.get("imaging", False),
            media=capabilities.get("media", False),
            events=capabilities.get("events", False),
            analytics=capabilities.get("analytics", False)
        )
    
    except Exception as e:
        logger.error(f"Erro ao obter capacidades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter capacidades: {str(e)}"
        )

@router.post("/discover", status_code=status.HTTP_200_OK)
def discover_devices(
    current_user = Depends(get_current_active_user)
):
    """
    Descobre dispositivos ONVIF na rede local.
    """
    try:
        # Usa o método estático para descobrir dispositivos
        devices = ONVIFController.discover_devices()
        
        return {"devices": devices}
    
    except Exception as e:
        logger.error(f"Erro ao descobrir dispositivos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao descobrir dispositivos: {str(e)}"
        )

@router.get("/cameras/{camera_id}/rtsp-channels", response_model=List[RTSPChannel])
def get_rtsp_channels(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Lista os canais RTSP disponíveis na câmera.
    """
    controller = get_onvif_controller(camera_id, db)
    
    try:
        # Obtém os canais RTSP
        channels = controller.get_rtsp_channels()
        
        # Converte para o modelo de resposta
        result = []
        for channel in channels:
            result.append(RTSPChannel(
                token=channel.get('token', ''),
                name=channel.get('name', ''),
                rtsp_url=channel.get('rtsp_url', ''),
                resolution=channel.get('resolution'),
                encoding=channel.get('encoding'),
                framerate=channel.get('framerate'),
                bitrate=channel.get('bitrate')
            ))
        
        return result
    
    except Exception as e:
        logger.error(f"Erro ao obter canais RTSP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter canais RTSP: {str(e)}"
        )
