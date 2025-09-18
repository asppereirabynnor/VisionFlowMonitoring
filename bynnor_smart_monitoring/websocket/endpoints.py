from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from typing import Optional
import logging
import json
import uuid
from sqlalchemy.orm import Session

from db.base import get_db
from models.models import User, Camera
from bynnor_smart_monitoring.websocket.manager import connection_manager
from bynnor_smart_monitoring.auth.auth import get_current_user, oauth2_scheme

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
)

async def get_token(
    token: Optional[str] = Query(None)
):
    if token is None:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    return token

async def get_ws_user(
    token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(token, db)
        return user
    except Exception as e:
        logger.error(f"Erro de autenticação WebSocket: {e}")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

@router.websocket("/events")
async def websocket_events(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket para receber notificações de eventos em tempo real.
    """
    # Gera um ID de cliente único
    client_id = f"events_{uuid.uuid4()}"
    
    # Autentica o usuário se o token for fornecido
    user = None
    if token:
        try:
            user = await get_current_user(token, db)
            client_id = f"events_user_{user.id}"
        except Exception as e:
            logger.error(f"Erro de autenticação WebSocket: {e}")
            await websocket.close(code=1008)  # Policy Violation
            return
    
    # Aceita a conexão
    await connection_manager.connect(websocket, client_id)
    
    try:
        # Envia mensagem de boas-vindas
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "message": "Conectado ao servidor de eventos"
        })
        
        # Loop principal para receber mensagens
        while True:
            # Aguarda mensagens do cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                # Processa diferentes tipos de mensagens
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    logger.warning(f"Tipo de mensagem desconhecido: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Tipo de mensagem desconhecido: {message_type}"
                    })
            
            except json.JSONDecodeError:
                logger.error(f"Mensagem inválida recebida: {data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Formato de mensagem inválido. Esperado JSON."
                })
    
    except WebSocketDisconnect:
        # Cliente desconectado
        connection_manager.disconnect(websocket, client_id)
    
    except Exception as e:
        # Erro inesperado
        logger.error(f"Erro no WebSocket de eventos: {e}")
        connection_manager.disconnect(websocket, client_id)

@router.websocket("/camera/{camera_id}")
async def websocket_camera(
    websocket: WebSocket,
    camera_id: int,
    token: Optional[str] = Query(None),
    quality: Optional[int] = Query(70),
    db: Session = Depends(get_db)
):
    """
    WebSocket para receber frames de uma câmera específica em tempo real.
    """
    # Verifica se a câmera existe
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        await websocket.close(code=1003)  # Unsupported Data
        return
    
    # Gera um ID de cliente único
    client_id = f"camera_{camera_id}_{uuid.uuid4()}"
    
    # Autentica o usuário se o token for fornecido
    user = None
    if token:
        try:
            user = await get_current_user(token, db)
            client_id = f"camera_{camera_id}_user_{user.id}"
        except Exception as e:
            logger.error(f"Erro de autenticação WebSocket: {e}")
            await websocket.close(code=1008)  # Policy Violation
            return
    
    # Aceita a conexão
    await connection_manager.connect(websocket, client_id)
    
    # Inscreve o cliente para receber frames da câmera
    connection_manager.subscribe_to_camera(client_id, str(camera_id))
    
    try:
        # Envia mensagem de boas-vindas
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "camera_id": camera_id,
            "camera_name": camera.name,
            "message": f"Conectado ao stream da câmera {camera.name}"
        })
        
        # Loop principal para receber mensagens
        while True:
            # Aguarda mensagens do cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                # Processa diferentes tipos de mensagens
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message_type == "set_quality":
                    new_quality = message.get("quality", 70)
                    if 10 <= new_quality <= 100:
                        quality = new_quality
                        await websocket.send_json({
                            "type": "quality_changed",
                            "quality": quality
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Qualidade deve estar entre 10 e 100"
                        })
                else:
                    logger.warning(f"Tipo de mensagem desconhecido: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Tipo de mensagem desconhecido: {message_type}"
                    })
            
            except json.JSONDecodeError:
                logger.error(f"Mensagem inválida recebida: {data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Formato de mensagem inválido. Esperado JSON."
                })
    
    except WebSocketDisconnect:
        # Cliente desconectado
        connection_manager.unsubscribe_from_camera(client_id, str(camera_id))
        connection_manager.disconnect(websocket, client_id)
    
    except Exception as e:
        # Erro inesperado
        logger.error(f"Erro no WebSocket da câmera: {e}")
        connection_manager.unsubscribe_from_camera(client_id, str(camera_id))
        connection_manager.disconnect(websocket, client_id)
