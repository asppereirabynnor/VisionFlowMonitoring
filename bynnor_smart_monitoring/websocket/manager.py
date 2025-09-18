import asyncio
import json
import logging
from typing import Dict, List, Any, Callable, Optional
from fastapi import WebSocket, WebSocketDisconnect
import base64
import cv2
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Gerenciador de conexões WebSocket."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.camera_streams: Dict[str, List[str]] = {}  # Mapeamento de câmeras para clientes
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Conecta um novo cliente WebSocket.
        
        Args:
            websocket: Conexão WebSocket
            client_id: ID único do cliente
        """
        await websocket.accept()
        
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
            
        self.active_connections[client_id].append(websocket)
        logger.info(f"Cliente WebSocket conectado: {client_id}")
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        """
        Desconecta um cliente WebSocket.
        
        Args:
            websocket: Conexão WebSocket
            client_id: ID do cliente
        """
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
                
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
                
        # Remove das assinaturas de câmeras
        for camera_id, clients in self.camera_streams.items():
            if client_id in clients:
                clients.remove(client_id)
                
        logger.info(f"Cliente WebSocket desconectado: {client_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """
        Envia uma mensagem para um cliente específico.
        
        Args:
            message: Mensagem a ser enviada
            client_id: ID do cliente
        """
        if client_id not in self.active_connections:
            return
            
        for connection in self.active_connections[client_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para {client_id}: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Envia uma mensagem para todos os clientes conectados.
        
        Args:
            message: Mensagem a ser enviada
        """
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Erro ao enviar broadcast para {client_id}: {e}")
    
    def subscribe_to_camera(self, client_id: str, camera_id: str):
        """
        Inscreve um cliente para receber frames de uma câmera.
        
        Args:
            client_id: ID do cliente
            camera_id: ID da câmera
        """
        if camera_id not in self.camera_streams:
            self.camera_streams[camera_id] = []
            
        if client_id not in self.camera_streams[camera_id]:
            self.camera_streams[camera_id].append(client_id)
            logger.info(f"Cliente {client_id} inscrito na câmera {camera_id}")
    
    def unsubscribe_from_camera(self, client_id: str, camera_id: str):
        """
        Cancela a inscrição de um cliente para uma câmera.
        
        Args:
            client_id: ID do cliente
            camera_id: ID da câmera
        """
        if camera_id in self.camera_streams and client_id in self.camera_streams[camera_id]:
            self.camera_streams[camera_id].remove(client_id)
            logger.info(f"Cliente {client_id} cancelou inscrição na câmera {camera_id}")
    
    async def send_camera_frame(self, camera_id: str, frame: np.ndarray, quality: int = 70):
        """
        Envia um frame de câmera para os clientes inscritos.
        
        Args:
            camera_id: ID da câmera
            frame: Frame BGR do OpenCV
            quality: Qualidade da compressão JPEG (1-100)
        """
        if camera_id not in self.camera_streams or not self.camera_streams[camera_id]:
            return
            
        try:
            # Converte o frame para JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            # Converte para base64
            base64_frame = base64.b64encode(buffer).decode('utf-8')
            
            # Cria a mensagem
            message = {
                'type': 'camera_frame',
                'camera_id': camera_id,
                'timestamp': datetime.now().isoformat(),
                'frame': base64_frame
            }
            
            # Envia para os clientes inscritos
            for client_id in self.camera_streams[camera_id]:
                await self.send_personal_message(message, client_id)
                
        except Exception as e:
            logger.error(f"Erro ao enviar frame da câmera {camera_id}: {e}")
    
    async def send_event_notification(self, event: Dict[str, Any], frame: Optional[np.ndarray] = None):
        """
        Envia uma notificação de evento para todos os clientes.
        
        Args:
            event: Informações do evento
            frame: Frame do evento (opcional)
        """
        try:
            # Cria a mensagem base
            message = {
                'type': 'event',
                'event_type': event.get('type', 'unknown'),
                'camera_id': event.get('camera_id', ''),
                'camera_name': event.get('camera_name', 'unknown'),
                'timestamp': event.get('timestamp', datetime.now().isoformat()),
                'confidence': event.get('confidence', 0.0),
                'metadata': event.get('metadata', {})
            }
            
            # Adiciona o frame se fornecido
            if frame is not None:
                # Converte o frame para JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                
                # Converte para base64
                base64_frame = base64.b64encode(buffer).decode('utf-8')
                message['frame'] = base64_frame
            
            # Envia para todos os clientes
            await self.broadcast(message)
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de evento: {e}")

# Instância global do gerenciador de conexões
connection_manager = ConnectionManager()
