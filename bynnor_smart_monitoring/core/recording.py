import cv2
import os
import time
import logging
import subprocess
import threading
import numpy as np
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class VideoRecorder:
    """Classe para gravação de vídeo a partir de eventos detectados."""
    
    def __init__(self, output_dir: str = "./events", 
                 pre_event_seconds: float = 3.0,
                 post_event_seconds: float = 5.0,
                 fps: int = 20,
                 codec: str = "mp4v"):
        """
        Inicializa o gravador de vídeo.
        
        Args:
            output_dir: Diretório para salvar os vídeos
            pre_event_seconds: Segundos de vídeo antes do evento
            post_event_seconds: Segundos de vídeo após o evento
            fps: Frames por segundo para gravação
            codec: Codec de vídeo (mp4v, avc1, etc.)
        """
        self.output_dir = output_dir
        self.pre_event_seconds = pre_event_seconds
        self.post_event_seconds = post_event_seconds
        self.fps = fps
        self.codec = codec
        self.frame_buffer = {}  # Buffer de frames por câmera
        self.max_buffer_frames = int(pre_event_seconds * fps)
        self.recording = {}  # Status de gravação por câmera
        self.recording_threads = {}
        
        # Cria o diretório de saída se não existir
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"VideoRecorder inicializado: buffer={pre_event_seconds}s, "
                   f"duração={pre_event_seconds + post_event_seconds}s, fps={fps}")
    
    def add_frame(self, frame: np.ndarray, metadata: Dict[str, Any]):
        """
        Adiciona um frame ao buffer.
        
        Args:
            frame: Frame BGR do OpenCV
            metadata: Metadados do frame
        """
        if frame is None or frame.size == 0:
            return
            
        camera_name = metadata.get('camera_name', 'unknown')
        timestamp = metadata.get('timestamp', time.time())
        
        # Inicializa o buffer para a câmera se necessário
        if camera_name not in self.frame_buffer:
            self.frame_buffer[camera_name] = []
            self.recording[camera_name] = False
        
        # Adiciona o frame ao buffer
        self.frame_buffer[camera_name].append({
            'frame': frame.copy(),
            'timestamp': timestamp
        })
        
        # Limita o tamanho do buffer
        while len(self.frame_buffer[camera_name]) > self.max_buffer_frames:
            self.frame_buffer[camera_name].pop(0)
    
    def start_recording(self, event: Dict[str, Any]):
        """
        Inicia a gravação de um evento.
        
        Args:
            event: Informações do evento
        """
        camera_name = event.get('camera_name', 'unknown')
        
        # Verifica se já está gravando para esta câmera
        if camera_name in self.recording and self.recording[camera_name]:
            logger.info(f"Já existe uma gravação em andamento para a câmera {camera_name}")
            return
        
        # Verifica se há frames no buffer
        if camera_name not in self.frame_buffer or not self.frame_buffer[camera_name]:
            logger.warning(f"Nenhum frame no buffer para a câmera {camera_name}")
            return
        
        # Marca como gravando
        self.recording[camera_name] = True
        
        # Inicia a thread de gravação
        thread = threading.Thread(
            target=self._record_event,
            args=(camera_name, event),
            daemon=True
        )
        self.recording_threads[camera_name] = thread
        thread.start()
        
        logger.info(f"Iniciando gravação para evento na câmera {camera_name}")
    
    def _record_event(self, camera_name: str, event: Dict[str, Any]):
        """
        Thread para gravação do evento.
        
        Args:
            camera_name: Nome da câmera
            event: Informações do evento
        """
        try:
            # Cria um nome de arquivo baseado no timestamp e tipo de evento
            timestamp = event.get('timestamp', time.time())
            event_type = event.get('type', 'unknown')
            dt = datetime.fromtimestamp(timestamp)
            filename = f"{camera_name}_{event_type}_{dt.strftime('%Y%m%d_%H%M%S')}"
            
            # Caminho para o vídeo
            video_path = os.path.join(self.output_dir, f"{filename}.mp4")
            
            # Caminho para o thumbnail
            thumbnail_path = os.path.join(self.output_dir, f"{filename}_thumb.jpg")
            
            # Caminho para os metadados
            metadata_path = os.path.join(self.output_dir, f"{filename}.json")
            
            # Copia os frames do buffer
            frames = self.frame_buffer[camera_name].copy()
            
            # Obtém as dimensões do frame
            if not frames:
                logger.error(f"Nenhum frame disponível para gravação na câmera {camera_name}")
                self.recording[camera_name] = False
                return
                
            sample_frame = frames[0]['frame']
            height, width = sample_frame.shape[:2]
            
            # Configura o gravador de vídeo
            fourcc = cv2.VideoWriter_fourcc(*self.codec)
            out = cv2.VideoWriter(video_path, fourcc, self.fps, (width, height))
            
            # Grava os frames do buffer
            for frame_data in frames:
                out.write(frame_data['frame'])
            
            # Continua gravando por mais alguns segundos
            start_time = time.time()
            frames_after_event = []
            
            while time.time() - start_time < self.post_event_seconds:
                # Verifica se há novos frames no buffer
                if camera_name in self.frame_buffer and self.frame_buffer[camera_name]:
                    current_buffer = self.frame_buffer[camera_name]
                    
                    # Verifica se há frames novos (que não estavam no buffer original)
                    if len(current_buffer) > 0 and current_buffer[-1] not in frames:
                        new_frame_data = current_buffer[-1]
                        out.write(new_frame_data['frame'])
                        frames_after_event.append(new_frame_data)
                
                # Pequena pausa para não sobrecarregar a CPU
                time.sleep(0.01)
            
            # Libera o gravador
            out.release()
            
            # Salva um thumbnail (último frame)
            if frames_after_event:
                cv2.imwrite(thumbnail_path, frames_after_event[-1]['frame'])
            elif frames:
                cv2.imwrite(thumbnail_path, frames[-1]['frame'])
            
            # Salva os metadados do evento
            with open(metadata_path, 'w') as f:
                metadata = {
                    'camera_name': camera_name,
                    'event_type': event_type,
                    'timestamp': timestamp,
                    'video_path': video_path,
                    'thumbnail_path': thumbnail_path,
                    'duration': self.pre_event_seconds + self.post_event_seconds,
                    'confidence': event.get('confidence', 0.0),
                    'bbox': event.get('bbox', []),
                    'additional_info': event.get('additional_info', {})
                }
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Evento gravado: {video_path}")
            
        except Exception as e:
            logger.error(f"Erro ao gravar evento: {e}")
        finally:
            # Marca como não gravando
            self.recording[camera_name] = False
    
    def is_recording(self, camera_name: str) -> bool:
        """Verifica se está gravando para uma câmera específica."""
        return self.recording.get(camera_name, False)

class EventManager:
    """Gerenciador de eventos do sistema de monitoramento."""
    
    def __init__(self, event_dir: str = "./events", db_session=None):
        """
        Inicializa o gerenciador de eventos.
        
        Args:
            event_dir: Diretório para armazenar eventos
            db_session: Sessão do banco de dados (opcional)
        """
        self.event_dir = event_dir
        self.db_session = db_session
        self.recorder = VideoRecorder(output_dir=event_dir)
        self.event_callbacks = []
        
        # Cria o diretório de eventos se não existir
        os.makedirs(event_dir, exist_ok=True)
    
    def add_frame(self, frame: np.ndarray, metadata: Dict[str, Any]):
        """
        Adiciona um frame ao buffer do gravador.
        
        Args:
            frame: Frame BGR do OpenCV
            metadata: Metadados do frame
        """
        self.recorder.add_frame(frame, metadata)
    
    def register_event_callback(self, callback):
        """Registra um callback para ser chamado quando um evento for detectado."""
        self.event_callbacks.append(callback)
    
    def process_event(self, event: Dict[str, Any], frame: np.ndarray = None):
        """
        Processa um evento detectado.
        
        Args:
            event: Informações do evento
            frame: Frame do evento (opcional)
        """
        try:
            # Inicia a gravação do evento
            self.recorder.start_recording(event)
            
            # Notifica os callbacks registrados
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Erro ao executar callback de evento: {e}")
            
            # Salva o evento no banco de dados se houver uma sessão
            if self.db_session:
                self._save_event_to_db(event)
                
            logger.info(f"Evento processado: {event.get('type')} na câmera {event.get('camera_name')}")
            
        except Exception as e:
            logger.error(f"Erro ao processar evento: {e}")
    
    def _save_event_to_db(self, event: Dict[str, Any]):
        """
        Salva o evento no banco de dados.
        
        Args:
            event: Informações do evento
        """
        try:
            # Importa o modelo Event apenas quando necessário
            from models.models import Event, EventType
            
            # Cria um novo evento
            new_event = Event(
                type=EventType(event.get('type', 'OBJECT')),
                description=f"Detecção de {event.get('type')}",
                confidence=int(event.get('confidence', 0.0) * 100),
                metadata=event,
                image_path=event.get('thumbnail_path', ''),
                video_path=event.get('video_path', ''),
                camera_id=event.get('camera_id')
            )
            
            # Adiciona e commita
            self.db_session.add(new_event)
            self.db_session.commit()
            
            logger.info(f"Evento salvo no banco de dados: ID={new_event.id}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar evento no banco de dados: {e}")
            if self.db_session:
                self.db_session.rollback()
    
    def get_recent_events(self, limit: int = 10, camera_name: str = None, 
                         event_type: str = None) -> List[Dict[str, Any]]:
        """
        Obtém eventos recentes.
        
        Args:
            limit: Número máximo de eventos
            camera_name: Filtrar por câmera (opcional)
            event_type: Filtrar por tipo de evento (opcional)
            
        Returns:
            Lista de eventos
        """
        try:
            # Se tiver banco de dados, usa ele
            if self.db_session:
                return self._get_events_from_db(limit, camera_name, event_type)
            
            # Caso contrário, lê os arquivos de metadados
            return self._get_events_from_files(limit, camera_name, event_type)
            
        except Exception as e:
            logger.error(f"Erro ao obter eventos recentes: {e}")
            return []
    
    def _get_events_from_db(self, limit: int, camera_name: str = None, 
                           event_type: str = None) -> List[Dict[str, Any]]:
        """Obtém eventos do banco de dados."""
        from models.models import Event, Camera
        from sqlalchemy import desc
        
        query = self.db_session.query(Event).order_by(desc(Event.created_at))
        
        if camera_name:
            query = query.join(Camera).filter(Camera.name == camera_name)
            
        if event_type:
            query = query.filter(Event.type == event_type)
            
        events = query.limit(limit).all()
        
        return [
            {
                'id': event.id,
                'type': event.type.value,
                'description': event.description,
                'confidence': event.confidence / 100.0,
                'timestamp': event.created_at.timestamp(),
                'camera_name': event.camera.name if event.camera else 'unknown',
                'image_path': event.image_path,
                'video_path': event.video_path,
                'metadata': event.metadata
            }
            for event in events
        ]
    
    def _get_events_from_files(self, limit: int, camera_name: str = None, 
                              event_type: str = None) -> List[Dict[str, Any]]:
        """Obtém eventos dos arquivos de metadados."""
        events = []
        
        # Lista todos os arquivos JSON no diretório de eventos
        json_files = list(Path(self.event_dir).glob('*.json'))
        
        # Ordena por data de modificação (mais recentes primeiro)
        json_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Lê os arquivos
        for json_file in json_files[:limit * 2]:  # Lê mais para poder filtrar
            try:
                with open(json_file, 'r') as f:
                    event = json.load(f)
                    
                    # Aplica filtros
                    if camera_name and event.get('camera_name') != camera_name:
                        continue
                        
                    if event_type and event.get('event_type') != event_type:
                        continue
                        
                    events.append(event)
                    
                    # Limita o número de eventos
                    if len(events) >= limit:
                        break
                        
            except Exception as e:
                logger.error(f"Erro ao ler arquivo de evento {json_file}: {e}")
        
        return events
