import logging
import json
import base64
import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from typing import Dict, Optional
from sqlalchemy.orm import Session
from bynnor_smart_monitoring.core.detection import ObjectDetector
from bynnor_smart_monitoring.auth.auth import verify_token_websocket, get_current_user
from db.base import get_db

router = APIRouter(
    tags=["Video Processing"],
)

logger = logging.getLogger(__name__)

# Dicionário para armazenar instâncias do detector de objetos
detectors: Dict[str, ObjectDetector] = {}

@router.websocket("/video-processing/{camera_id}")
async def video_processing_websocket(websocket: WebSocket, camera_id: int, token: Optional[str] = None):
    """
    Endpoint WebSocket para processar vídeo em tempo real com detecção YOLO.
    
    O cliente deve enviar frames de vídeo como strings base64 e receberá de volta
    os frames processados com as detecções desenhadas.
    
    O token JWT deve ser fornecido como query parameter para autenticação.
    """
    logger.info(f"Tentativa de conexão WebSocket para processamento de vídeo da câmera {camera_id}")
    
    # Obter o token do query parameter
    query_params = dict(websocket.query_params)
    logger.info(f"Query parameters recebidos: {query_params}")
    token = query_params.get("token")
    
    # Verificar autenticação
    if not token:
        logger.error("Token não fornecido na conexão WebSocket")
        await websocket.close(code=1008, reason="Token de autenticação não fornecido")
        return
    
    logger.info(f"Token recebido: {token[:20]}...")
    
    # Obter sessão do banco de dados
    db = next(get_db())
    
    # Verificar o token
    logger.info("Verificando token WebSocket...")
    user = await verify_token_websocket(token, db)
    if not user:
        logger.error("Token inválido ou expirado na conexão WebSocket")
        await websocket.close(code=1008, reason="Token inválido ou expirado")
        return
    
    logger.info(f"Usuário {user.email} autenticado com sucesso para WebSocket da câmera {camera_id}")
    
    try:
        await websocket.accept()
        logger.info(f"Nova conexão WebSocket aceita para processamento de vídeo da câmera {camera_id}")
    except Exception as e:
        logger.error(f"Erro ao aceitar conexão WebSocket: {str(e)}")
        return
    
    # Inicializa o detector para esta conexão
    detector_id = f"camera_{camera_id}_{id(websocket)}"
    try:
        detectors[detector_id] = ObjectDetector(model_path='yolov8n.pt', conf_threshold=0.5)
        logger.info(f"Detector inicializado para câmera {camera_id}")
    except Exception as e:
        logger.error(f"Erro ao inicializar detector para câmera {camera_id}: {e}")
        await websocket.send_json({
            "error": f"Erro ao inicializar detector: {str(e)}"
        })
        # Continuamos mesmo sem o detector
    
    try:
        while True:
            # Recebe o frame como JSON com a imagem em base64
            logger.debug(f"Aguardando frame da câmera {camera_id}")
            try:
                data = await websocket.receive_text()
                logger.debug(f"Frame recebido da câmera {camera_id}")
                
                json_data = json.loads(data)
                base64_frame = json_data.get("frame")
                if not base64_frame:
                    logger.warning(f"Frame recebido sem dados de imagem da câmera {camera_id}")
                    continue
                
                # Converte base64 para imagem OpenCV
                img_data = base64.b64decode(base64_frame.split(',')[1] if ',' in base64_frame else base64_frame)
                
                # Processa o frame com o detector
                logger.debug(f"Processando frame da câmera {camera_id} com detector")
                detector = detectors.get(detector_id)
                
                # Converte o frame para o formato correto
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    logger.warning(f"Não foi possível decodificar o frame da câmera {camera_id}")
                    await websocket.send_json({"error": "Não foi possível decodificar o frame"})
                    continue
                
                # Cria uma cópia do frame para processamento
                frame_with_detections = frame.copy()
                detection_data = []
                
                # Tenta usar o detector se estiver disponível
                if detector and hasattr(detector, 'model') and detector.model is not None:
                    try:
                        # Detecta objetos no frame
                        detections = detector.detect(frame)
                        
                        # Desenha as detecções no frame
                        for detection in detections:
                            x, y, w, h = detection.bbox_pixels
                            
                            # Garante que as coordenadas estão dentro dos limites do frame
                            x = max(0, min(frame.shape[1] - 1, x))
                            y = max(0, min(frame.shape[0] - 1, y))
                            w = min(w, frame.shape[1] - x)
                            h = min(h, frame.shape[0] - y)
                            
                            # Desenha o retângulo com cores diferentes para cada classe
                            color = (0, 255, 0)  # Verde para pessoa
                            if detection.class_name == 'train':
                                color = (0, 165, 255)  # Laranja para trem
                            
                            cv2.rectangle(frame_with_detections, (x, y), (x + w, y + h), color, 2)
                            
                            # Adiciona um fundo semi-transparente para o texto
                            label = f"{detection.class_name}: {detection.confidence:.2f}"
                            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                            cv2.rectangle(frame_with_detections, (x, y - text_h - 10), (x + text_w, y), color, -1)
                            
                            # Adiciona o texto
                            cv2.putText(frame_with_detections, label, (x, y - 5), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
                        # Formata as detecções para envio
                        detection_data = [
                            {
                                "class_id": d.class_id,
                                "class_name": d.class_name,
                                "confidence": d.confidence,
                                "bbox": d.bbox_pixels
                            } for d in detections
                        ]
                        
                        logger.debug(f"Frame processado com {len(detections)} detecções")
                    except Exception as e:
                        logger.error(f"Erro ao processar frame com detector: {e}")
                        # Adiciona uma mensagem de erro no frame
                        cv2.putText(frame_with_detections, "Erro no detector YOLO", (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    # Adiciona uma mensagem no frame indicando que o detector não está disponível
                    cv2.putText(frame_with_detections, "Detector YOLO não disponível", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    logger.warning(f"Detector não disponível para câmera {camera_id}")
                
                # Converte o frame processado para base64
                _, buffer = cv2.imencode('.jpg', frame_with_detections)
                processed_frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Envia o frame processado e as detecções
                await websocket.send_json({
                    "processed_frame": f"data:image/jpeg;base64,{processed_frame_base64}",
                    "detections": detection_data
                })
                logger.debug(f"Frame processado enviado para câmera {camera_id}")
            except json.JSONDecodeError:
                logger.error("Erro ao decodificar JSON do WebSocket")
                continue
            except Exception as e:
                logger.error(f"Erro ao processar frame: {str(e)}")
                continue
    
    except Exception as e:
        logger.error(f"Erro na conexão WebSocket: {str(e)}")
    finally:
        # Limpa o detector quando a conexão é fechada
        if detector_id in detectors:
            del detectors[detector_id]
        logger.info(f"Conexão WebSocket fechada para câmera {camera_id}")
