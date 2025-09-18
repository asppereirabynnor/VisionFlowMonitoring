import os
import sys
import logging
import time
import uvicorn

# Adiciona o diretório atual ao PYTHONPATH para resolver importações
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import threading
import time
from typing import Optional, Dict, Any
import uvicorn
from dotenv import load_dotenv
import asyncio

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Importações dos módulos da aplicação
from db.base import engine, Base, get_db
from bynnor_smart_monitoring.api import cameras, events, users, onvif, video_processing, video_download, realtime_detection
from bynnor_smart_monitoring.auth import auth
from bynnor_smart_monitoring.websocket import endpoints
from bynnor_smart_monitoring.core.camera import CameraManager
from bynnor_smart_monitoring.core.detection import ObjectDetector
from bynnor_smart_monitoring.core.recording import EventManager
from bynnor_smart_monitoring.websocket.manager import connection_manager

# Inicialização dos componentes
camera_manager = CameraManager()
event_manager = EventManager()
object_detector = None

# Função para inicializar o detector de objetos
def init_object_detector():
    global object_detector
    try:
        model_path = os.getenv('YOLO_MODEL_PATH', 'yolov8n.pt')
        object_detector = ObjectDetector(model_path=model_path)
        logger.info(f'Detector de objetos inicializado com o modelo {model_path}')
    except Exception as e:
        logger.error(f'Erro ao inicializar detector de objetos: {e}')

# Função para processar frames das câmeras
def process_camera_frames():
    while True:
        try:
            # Processa cada câmera ativa
            for camera_id, camera in camera_manager.cameras.items():
                # Obtém o frame mais recente
                frame = camera.get_latest_frame()
                if frame is None:
                    continue
                
                # Cria metadados do frame
                metadata = {
                    'camera_id': camera_id,
                    'camera_name': camera.name,
                    'timestamp': time.time()
                }
                
                # Adiciona o frame ao buffer do gravador de eventos
                event_manager.add_frame(frame, metadata)
                
                # Detecta objetos se o detector estiver disponível
                if object_detector:
                    detections = object_detector.detect(frame)
                    if detections:
                        # Processa detecções e gera eventos se necessário
                        for detection in detections:
                            if detection.confidence > 0.5:  # Limiar de confiança
                                # Cria um evento
                                event = {
                                    'type': detection.class_name,
                                    'camera_id': camera_id,
                                    'camera_name': camera.name,
                                    'confidence': detection.confidence,
                                    'bbox': detection.bbox,
                                    'timestamp': time.time()
                                }
                                
                                # Processa o evento
                                event_manager.process_event(event, frame)
                                
                                # Envia notificação via WebSocket
                                asyncio.run(connection_manager.send_event_notification(event, frame))
                
                # Envia o frame para clientes WebSocket inscritos
                asyncio.run(connection_manager.send_camera_frame(camera_id, frame))
            
            # Pequena pausa para não sobrecarregar a CPU
            time.sleep(0.05)
            
        except Exception as e:
            logger.error(f'Erro ao processar frames das câmeras: {e}')
            time.sleep(1)  # Pausa maior em caso de erro

# Gerenciador de contexto para inicialização e encerramento
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização
    logger.info('Inicializando aplicação...')
    
    # Cria as tabelas no banco de dados
    Base.metadata.create_all(bind=engine)
    
    # Inicializa o detector de objetos em uma thread separada
    detector_thread = threading.Thread(target=init_object_detector, daemon=True)
    detector_thread.start()
    
    # Inicia o processamento de frames em uma thread separada
    process_thread = threading.Thread(target=process_camera_frames, daemon=True)
    process_thread.start()
    
    logger.info('Aplicação inicializada com sucesso!')
    yield
    
    # Encerramento
    logger.info('Encerrando aplicação...')
    
    # Para todas as câmeras
    camera_manager.stop_all_cameras()
    
    logger.info('Aplicação encerrada com sucesso!')

# Configuração da aplicação
app = FastAPI(
    title='Bynnor Smart Monitoring API',
    description='API para sistema de monitoramento inteligente com câmeras IP',
    version='0.1.0',
    docs_url='/docs',
    redoc_url='/redoc',
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],  # Em produção, substituir por domínios específicos
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Length"],
    max_age=600
)

# Rotas da API
@app.get('/')
async def root():
    return {'message': 'Bem-vindo à API do Bynnor Smart Monitoring'}

# Health Check
@app.get('/health')
async def health_check():
    return {
        'status': 'healthy',
        'cameras': len(camera_manager.cameras),
        'detector': 'loaded' if object_detector else 'not_loaded'
    }

@app.get('/test-cameras')
async def test_cameras():
    return {'message': 'Endpoint de teste para câmeras funcionando!'}

# Inclui os routers
logger.info("Registrando routers...")
app.include_router(auth.router, prefix='/auth', tags=['Autenticação'])
app.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(onvif.router, prefix="/onvif", tags=["onvif"])
app.include_router(video_processing.router, tags=["video-processing"])
app.include_router(video_download.router, prefix="/video-download", tags=["video-download"])
app.include_router(realtime_detection.router, prefix="/realtime-detection", tags=["realtime-detection"])
app.include_router(endpoints.router)

logger.info("Todos os routers registrados com sucesso!")

# Listar todas as rotas registradas
for route in app.routes:
    logger.info(f"Rota registrada: {route.path} - {route.methods if hasattr(route, 'methods') else 'WebSocket'}")


# Pasta para arquivos estáticos (eventos, uploads, etc.)
os.makedirs('static', exist_ok=True)
app.mount('/static', StaticFiles(directory='static'), name='static')

if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 8000)),
        reload=True
    )
