import cv2
import numpy as np
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os
import sys
import importlib

logger = logging.getLogger(__name__)

# Importação condicional para evitar erros se o modelo não estiver instalado
try:
    logger.debug(f"Python path: {sys.path}")
    logger.debug(f"Tentando importar ultralytics")
    if importlib.util.find_spec('ultralytics') is not None:
        logger.debug(f"Módulo ultralytics encontrado")
        from ultralytics import YOLO
        logger.debug(f"Módulo YOLO importado com sucesso")
        YOLO_AVAILABLE = True
    else:
        logger.debug(f"Módulo ultralytics não encontrado")
        YOLO_AVAILABLE = False
except Exception as e:
    logger.error(f"Erro ao importar YOLO: {e}")
    YOLO_AVAILABLE = False

@dataclass
class DetectionResult:
    """Resultado da detecção de objetos em um frame."""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x, y, width, height] em coordenadas normalizadas (0-1)
    frame_width: int
    frame_height: int
    
    @property
    def bbox_pixels(self) -> List[int]:
        """Retorna a bounding box em pixels.
        
        Converte de [x_center, y_center, width, height] para [x_top_left, y_top_left, width, height]
        """
        # Calcula as coordenadas do canto superior esquerdo a partir do centro
        x_center = self.bbox[0] * self.frame_width
        y_center = self.bbox[1] * self.frame_height
        w = self.bbox[2] * self.frame_width
        h = self.bbox[3] * self.frame_height
        
        # Calcula o canto superior esquerdo
        x = int(x_center - w/2)
        y = int(y_center - h/2)
        
        # Garante que os valores são inteiros positivos
        x = max(0, x)
        y = max(0, y)
        w = int(w)
        h = int(h)
        
        return [x, y, w, h]
    
    @property
    def center(self) -> tuple:
        """Retorna as coordenadas do centro da detecção."""
        x, y, w, h = self.bbox_pixels
        return (x + w // 2, y + h // 2)

class ObjectDetector:
    """Classe para detecção de objetos usando YOLOv8."""
    
    def __init__(self, model_path: str = 'yolov8n.pt', conf_threshold: float = 0.5):
        """
        Inicializa o detector de objetos.
        
        Args:
            model_path: Caminho para o modelo YOLOv8 pré-treinado ou nome do modelo
            conf_threshold: Limiar de confiança para as detecções
        """
        self.conf_threshold = conf_threshold
        self.model = None
        self.class_names = {}
        
        if not YOLO_AVAILABLE:
            logger.warning("Ultralytics YOLO não está disponível. A detecção de objetos não funcionará.")
            return
            
        try:
            self.model = self._load_model(model_path)
            self.class_names = self.model.names if hasattr(self.model, 'names') else {}
            logger.info(f"Detector de objetos inicializado com modelo {model_path}")
            logger.info(f"Classes disponíveis: {list(self.class_names.values())}")
        except Exception as e:
            logger.error(f"Erro ao inicializar o detector de objetos: {e}")
    
    def _load_model(self, model_path: str):
        """Carrega o modelo YOLOv8."""
        try:
            # Tenta carregar o modelo localmente
            if os.path.exists(model_path):
                model = YOLO(model_path)
            else:
                # Se não encontrar localmente, tenta baixar o modelo
                model = YOLO(model_path)
                
            return model
            
        except Exception as e:
            logger.error(f"Erro ao carregar o modelo {model_path}: {e}")
            raise
    
    def detect(self, frame: np.ndarray, classes: Optional[List[str]] = None, conf: Optional[float] = None) -> List[DetectionResult]:
        """
        Detecta objetos em um frame de vídeo.
        
        Args:
            frame: Frame BGR do OpenCV
            classes: Lista de classes para filtrar as detecções (opcional)
            conf: Limiar de confiança para as detecções (opcional)
            
        Returns:
            Lista de objetos detectados
        """
        if frame is None or frame.size == 0 or self.model is None:
            return []
            
        height, width = frame.shape[:2]
        
        try:
            # Define o limiar de confiança a ser usado
            confidence = conf if conf is not None else self.conf_threshold
            
            # Executa a detecção
            results = self.model(frame, verbose=False, conf=confidence)[0]
            
            # Processa os resultados
            detections = []
            
            for result in results.boxes.data.tolist():
                x1, y1, x2, y2, conf, class_id = result
                
                # Obtém o nome da classe
                class_id = int(class_id)
                class_name = self.class_names.get(class_id, f"classe_{class_id}")
                
                # Filtra por classes se especificado
                if classes and class_name not in classes:
                    continue
                
                # Converte para coordenadas normalizadas [x_center, y_center, width, height]
                x_center = ((x1 + x2) / 2) / width
                y_center = ((y1 + y2) / 2) / height
                w = (x2 - x1) / width
                h = (y2 - y1) / height
                
                # Garante que as coordenadas estão no intervalo [0, 1]
                x_center = max(0.0, min(1.0, x_center))
                y_center = max(0.0, min(1.0, y_center))
                w = max(0.0, min(1.0, w))
                h = max(0.0, min(1.0, h))
                
                # Adiciona à lista de detecções
                detection = DetectionResult(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=conf,
                    bbox=[x_center, y_center, w, h],
                    frame_width=width,
                    frame_height=height
                )
                
                detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"Erro durante a detecção de objetos: {e}")
            return []
    
    def draw_detections(self, frame: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """
        Desenha as detecções no frame.
        
        Args:
            frame: Frame BGR do OpenCV
            detections: Lista de detecções
            
        Returns:
            Frame com as detecções desenhadas
        """
        if frame is None or len(detections) == 0:
            return frame
            
        frame_copy = frame.copy()
        height, width = frame_copy.shape[:2]
        
        for detection in detections:
            x, y, w, h = detection.bbox_pixels
            
            # Garante que as coordenadas estão dentro dos limites do frame
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
            w = min(w, width - x)
            h = min(h, height - y)
            
            # Cor baseada na classe
            color = (0, 255, 0)  # Verde para pessoa
            if detection.class_name == 'train':
                color = (0, 165, 255)  # Laranja para trem
            elif detection.class_name == 'car':
                color = (0, 0, 255)  # Vermelho para carro
            elif detection.class_name == 'truck':
                color = (255, 0, 0)  # Azul para caminhão
            else:
                color = self._get_color(detection.class_id)
            
            # Desenha o retângulo
            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), color, 2)
            
            # Adiciona um fundo para o texto
            label = f"{detection.class_name}: {detection.confidence:.2f}"
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame_copy, (x, y - text_h - 10), (x + text_w, y), color, -1)
            
            # Adiciona o texto
            cv2.putText(frame_copy, label, (x, y - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame_copy
    
    def _get_color(self, class_id: int) -> tuple:
        """Retorna uma cor única para cada classe."""
        # Gera uma cor consistente baseada no ID da classe
        np.random.seed(class_id)
        return tuple(map(int, np.random.randint(0, 255, 3)))
    
    def _draw_label(self, image: np.ndarray, text: str, position: tuple, color: tuple):
        """Desenha um rótulo com fundo preto."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        # Tamanho do texto
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Posição do retângulo de fundo
        x, y = position
        rect_x1 = x
        rect_y1 = y - text_height - 5
        rect_x2 = x + text_width + 5
        rect_y2 = y + 5
        
        # Desenha o retângulo de fundo
        cv2.rectangle(image, (rect_x1, rect_y1), (rect_x2, rect_y2), (0, 0, 0), -1)
        
        # Desenha o texto
        cv2.putText(
            image, text, (x, y), 
            font, font_scale, color, thickness, 
            cv2.LINE_AA
        )

class EventDetector:
    """Classe para detectar eventos com base nas detecções de objetos."""
    
    def __init__(self, detector: ObjectDetector, min_confidence: float = 0.5):
        self.detector = detector
        self.min_confidence = min_confidence
        self.classes_of_interest = ['person', 'car', 'truck', 'bus', 'bicycle', 'motorcycle']
        self.last_event_time = {}
        self.min_event_interval = 5.0  # segundos entre eventos da mesma classe
    
    def process_frame(self, frame: np.ndarray, metadata: dict) -> dict:
        """
        Processa um frame para detecção de eventos.
        
        Args:
            frame: Frame BGR do OpenCV
            metadata: Metadados do frame
            
        Returns:
            Dicionário com os resultados do processamento
        """
        if frame is None:
            return {}
            
        # Detecta objetos no frame
        detections = self.detector.detect(frame)
        
        # Filtra apenas as classes de interesse com confiança mínima
        filtered_detections = [
            d for d in detections 
            if d.class_name in self.classes_of_interest and d.confidence >= self.min_confidence
        ]
        
        # Verifica eventos
        events = self._check_events(filtered_detections, metadata)
        
        # Desenha as detecções no frame
        frame_with_detections = self.detector.draw_detections(frame, filtered_detections)
        
        return {
            'detections': filtered_detections,
            'events': events,
            'frame_with_detections': frame_with_detections,
            'timestamp': metadata.get('timestamp', 0),
            'camera_name': metadata.get('camera_name', 'unknown')
        }
    
    def _check_events(self, detections: List[DetectionResult], metadata: dict) -> List[dict]:
        """Verifica se há eventos de interesse nas detecções."""
        events = []
        current_time = metadata.get('timestamp', time.time())
        camera_name = metadata.get('camera_name', 'unknown')
        
        # Agrupa detecções por classe
        detections_by_class = {}
        for detection in detections:
            if detection.class_name not in detections_by_class:
                detections_by_class[detection.class_name] = []
            detections_by_class[detection.class_name].append(detection)
        
        # Verifica eventos para cada classe
        for class_name, class_detections in detections_by_class.items():
            # Chave única para o evento (câmera + classe)
            event_key = f"{camera_name}_{class_name}"
            
            # Verifica se já passou tempo suficiente desde o último evento desta classe
            last_time = self.last_event_time.get(event_key, 0)
            if current_time - last_time < self.min_event_interval:
                continue
                
            # Encontra a detecção com maior confiança
            best_detection = max(class_detections, key=lambda d: d.confidence)
            
            # Cria o evento
            event = {
                'type': class_name,
                'confidence': best_detection.confidence,
                'bbox': best_detection.bbox,
                'timestamp': current_time,
                'camera_name': camera_name
            }
            
            events.append(event)
            self.last_event_time[event_key] = current_time
        
        return events
