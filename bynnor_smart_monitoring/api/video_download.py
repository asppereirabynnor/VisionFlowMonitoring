import os
import tempfile
import logging
import uuid
import shutil
import time
from typing import List, Optional
import asyncio
import aiohttp
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Body, Security
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyQuery
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from db.base import get_db
from bynnor_smart_monitoring.auth.auth import get_current_user
from bynnor_smart_monitoring.core.detection import ObjectDetector
from models.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

# Definir esquema de segurança para token via query parameter
api_key_query = APIKeyQuery(name="token", auto_error=False)

# Diretório para armazenar vídeos temporários
TEMP_VIDEO_DIR = os.path.join(tempfile.gettempdir(), "bynnor_videos")
os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)

# Variável para controlar a última limpeza
last_cleanup_time = 0
# Intervalo de limpeza em segundos (4 horas)
CLEANUP_INTERVAL = 4 * 60 * 60

# Modelo para solicitação de processamento de vídeo
class VideoProcessRequest(BaseModel):
    video_url: HttpUrl
    detect_classes: Optional[List[str]] = None
    confidence_threshold: float = 0.5

# Modelo para resposta de upload de vídeo
class VideoUploadResponse(BaseModel):
    processed_video_id: str
    message: str

# Modelo para resposta de processamento de vídeo
class VideoProcessResponse(BaseModel):
    processed_video_id: str
    message: str

# Modelo para resposta de status do vídeo
class VideoStatusResponse(BaseModel):
    video_id: str
    status: str
    progress: Optional[float] = None
    error: Optional[str] = None
    total_frames: Optional[int] = None
    processed_frames: Optional[int] = None

# Dicionário para rastrear tarefas em andamento
processing_tasks = {}

async def download_video(url: str, target_path: str):
    """Download um vídeo de uma URL para um caminho local."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail=f"Não foi possível baixar o vídeo. Status: {response.status}")
                
                with open(target_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024 * 1024)  # 1MB por chunk
                        if not chunk:
                            break
                        f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Erro ao baixar vídeo: {str(e)}")
        return False

async def process_video_with_yolo(
    video_path: str, 
    output_path: str, 
    task_id: str,
    detect_classes: Optional[List[str]] = None,
    confidence_threshold: float = 0.5
):
    """Processa um vídeo com YOLO e salva o resultado."""
    try:
        detector = ObjectDetector()
        
        # Abrir o vídeo
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Não foi possível abrir o vídeo")
        
        # Obter informações do vídeo
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Atualizar informações da tarefa com o total de frames
        processing_tasks[task_id]["total_frames"] = total_frames
        processing_tasks[task_id]["processed_frames"] = 0
        
        # Configurar o writer para o vídeo de saída
        # Tentando usar codec mp4v que é mais amplamente suportado
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if not out.isOpened():
                # Fallback para XVID se mp4v falhar
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                output_path = output_path.replace('.mp4', '.avi')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                logger.info(f"Usando codec XVID com saída em formato AVI: {output_path}")
        except Exception as e:
            logger.error(f"Erro ao configurar VideoWriter: {str(e)}")
            raise
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Processar o frame com YOLO
            results = detector.detect(frame, classes=detect_classes, conf=confidence_threshold)
            
            # Desenhar as detecções no frame
            processed_frame = detector.draw_detections(frame, results)
            
            # Escrever o frame processado no vídeo de saída
            out.write(processed_frame)
            
            frame_count += 1
            
            # Atualizar progresso a cada frame
            processing_tasks[task_id]["processed_frames"] = frame_count
            processing_tasks[task_id]["progress"] = (frame_count / total_frames) * 100
            
            # Logar progresso a cada 100 frames
            if frame_count % 100 == 0:
                logger.info(f"Processados {frame_count}/{total_frames} frames ({processing_tasks[task_id]['progress']:.1f}%)")
        
        # Garantir que o progresso seja 100% ao finalizar
        processing_tasks[task_id]["progress"] = 100.0
        processing_tasks[task_id]["processed_frames"] = total_frames
        
        # Liberar recursos
        cap.release()
        out.release()
        
        return True
    except Exception as e:
        logger.error(f"Erro ao processar vídeo com YOLO: {str(e)}")
        return False

async def handle_video_processing(
    task_id: str,
    video_url: str = None,
    video_path: str = None,
    detect_classes: Optional[List[str]] = None,
    confidence_threshold: float = 0.5
):
    """Função de background para download e processamento de vídeo."""
    try:
        # Criar caminhos para os arquivos
        output_video_path = os.path.join(TEMP_VIDEO_DIR, f"output_{task_id}.mp4")
        
        # Inicializar campos de progresso
        processing_tasks[task_id]["progress"] = 0.0
        processing_tasks[task_id]["total_frames"] = 0
        processing_tasks[task_id]["processed_frames"] = 0
        
        # Se for um upload de arquivo, o vídeo já está no sistema
        if video_path:
            input_video_path = video_path
        else:
            # Caso contrário, é uma URL e precisamos baixar
            input_video_path = os.path.join(TEMP_VIDEO_DIR, f"input_{task_id}.mp4")
            
            # Atualizar status
            processing_tasks[task_id]["status"] = "downloading"
            
            # Download do vídeo
            download_success = await download_video(video_url, input_video_path)
            if not download_success:
                processing_tasks[task_id]["status"] = "failed"
                processing_tasks[task_id]["error"] = "Falha ao baixar o vídeo"
                return
        
        # Atualizar status
        processing_tasks[task_id]["status"] = "processing"
        
        # Processar o vídeo
        process_success = await process_video_with_yolo(
            input_video_path, 
            output_video_path,
            task_id,
            detect_classes, 
            confidence_threshold
        )
        
        if not process_success:
            processing_tasks[task_id]["status"] = "failed"
            processing_tasks[task_id]["error"] = "Falha ao processar o vídeo"
            return
        
        # Atualizar status para concluído
        processing_tasks[task_id]["status"] = "completed"
        processing_tasks[task_id]["output_path"] = output_video_path
        processing_tasks[task_id]["progress"] = 100.0
        
        # Remover o vídeo de entrada para economizar espaço
        if os.path.exists(input_video_path):
            os.remove(input_video_path)
            
    except Exception as e:
        logger.error(f"Erro no processamento do vídeo {task_id}: {str(e)}")
        processing_tasks[task_id]["status"] = "failed"
        processing_tasks[task_id]["error"] = str(e)

@router.post("/process-video", response_model=VideoProcessResponse)
async def process_video(
    request: VideoProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint para processar um vídeo a partir de uma URL."""
    # Gerar ID único para a tarefa
    task_id = str(uuid.uuid4())
    
    # Registrar a tarefa
    processing_tasks[task_id] = {
        "status": "queued",
        "user_id": current_user.id,
        "video_url": request.video_url,
        "created_at": time.time()
    }
    
    # Adicionar tarefa em segundo plano
    background_tasks.add_task(
        handle_video_processing,
        task_id,
        video_url=str(request.video_url),
        detect_classes=request.detect_classes,
        confidence_threshold=request.confidence_threshold
    )
    
    return VideoProcessResponse(
        processed_video_id=task_id,
        message="Processamento de vídeo iniciado. Use o endpoint /video-status/{video_id} para verificar o status."
    )

@router.get("/video-status/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: str,
    current_user: User = Depends(get_current_user)
):
    """Verifica o status de processamento de um vídeo."""
    # Verificar se é hora de fazer limpeza
    check_and_cleanup()
    
    if video_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Tarefa de processamento não encontrada")
    
    task = processing_tasks[video_id]
    
    # Verificar se o usuário tem acesso a esta tarefa
    if task["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso")
    
    # Construir resposta com informações de progresso
    response = VideoStatusResponse(
        video_id=video_id,
        status=task["status"],
        progress=task.get("progress"),
        total_frames=task.get("total_frames"),
        processed_frames=task.get("processed_frames")
    )
    
    if task["status"] == "failed" and "error" in task:
        response.error = task["error"]
    
    return response

@router.post("/upload-video", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    detect_classes: Optional[List[str]] = Form(None),
    confidence_threshold: float = Form(0.5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint para fazer upload e processar um vídeo local."""
    # Verificar se o arquivo é um vídeo
    content_type = file.content_type
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="O arquivo enviado não é um vídeo")
    
    # Gerar ID único para a tarefa
    task_id = str(uuid.uuid4())
    
    # Criar caminho para salvar o arquivo temporário
    temp_file_path = os.path.join(TEMP_VIDEO_DIR, f"upload_{task_id}{os.path.splitext(file.filename)[1]}")
    
    try:
        # Salvar o arquivo enviado
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Registrar a tarefa
        processing_tasks[task_id] = {
            "status": "queued",
            "user_id": current_user.id,
            "filename": file.filename,
            "created_at": time.time()
        }
        
        # Adicionar tarefa em segundo plano
        background_tasks.add_task(
            handle_video_processing,
            task_id,
            video_path=temp_file_path,
            detect_classes=detect_classes,
            confidence_threshold=confidence_threshold
        )
        
        return VideoUploadResponse(
            processed_video_id=task_id,
            message="Upload e processamento de vídeo iniciados. Use o endpoint /video-status/{video_id} para verificar o status."
        )
    except Exception as e:
        # Em caso de erro, remover o arquivo temporário se existir
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Erro ao processar o upload: {str(e)}")

@router.get("/download-video/{video_id}")
async def download_processed_video(
    video_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download do vídeo processado."""
    # Logs para depuração
    logger.info(f"Solicitado download do vídeo {video_id} pelo usuário {current_user.email}")
    
    # Verificar se é hora de fazer limpeza
    check_and_cleanup()
    
    if video_id not in processing_tasks:
        logger.error(f"Vídeo {video_id} não encontrado nas tarefas de processamento")
        raise HTTPException(status_code=404, detail="Vídeo processado não encontrado")
    
    task = processing_tasks[video_id]
    logger.info(f"Tarefa encontrada para vídeo {video_id}: status={task['status']}")
    
    # Verificar se o usuário tem acesso a esta tarefa
    if task["user_id"] != current_user.id and not current_user.is_admin:
        logger.error(f"Acesso negado: usuário {current_user.id} tentando acessar vídeo do usuário {task['user_id']}")
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso")
    
    # Verificar se o processamento foi concluído
    if task["status"] != "completed":
        logger.error(f"Vídeo {video_id} não está pronto para download. Status atual: {task['status']}")
        raise HTTPException(
            status_code=400, 
            detail=f"O vídeo ainda não está pronto para download. Status atual: {task['status']}"
        )
    
    output_path = task["output_path"]
    logger.info(f"Caminho do arquivo para download: {output_path}")
    
    if not os.path.exists(output_path):
        logger.error(f"Arquivo não encontrado no caminho: {output_path}")
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado no servidor")
    
    # Verificar tamanho e permissões do arquivo
    try:
        file_size = os.path.getsize(output_path)
        file_permissions = oct(os.stat(output_path).st_mode)[-3:]
        logger.info(f"Arquivo encontrado: tamanho={file_size} bytes, permissões={file_permissions}")
    except Exception as e:
        logger.error(f"Erro ao verificar arquivo: {str(e)}")
    
    try:
        logger.info(f"Enviando arquivo {output_path} como resposta")
        
        # Usar o tipo de arquivo e nome específico solicitado
        file_ext = os.path.splitext(output_path)[1].lower()
        if file_ext == '.avi':
            media_type = "video/x-msvideo"
            filename = f"processed_video_{video_id}.avi"
        else:
            media_type = "video/mp4"
            filename = f"processed_video_{video_id}.mp4"
            
        logger.info(f"Tipo de mídia detectado: {media_type}, nome do arquivo: {filename}")
        
        # Adicionar cabeçalhos adicionais para melhorar a compatibilidade com navegadores
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        
        # Verificar se o arquivo existe e tem tamanho válido
        if os.path.getsize(output_path) == 0:
            logger.error(f"Arquivo vazio: {output_path}")
            raise HTTPException(status_code=500, detail="O arquivo de vídeo processado está vazio")
            
        return FileResponse(
            path=output_path, 
            filename=filename,
            media_type=media_type,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Erro ao enviar arquivo como resposta: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar arquivo: {str(e)}")


# Limpeza periódica de vídeos antigos (pode ser chamado por um scheduler)
def cleanup_old_videos(max_age_hours: int = 24):
    """Remove vídeos processados antigos."""
    global last_cleanup_time
    
    current_time = time.time()
    
    # Verificar tarefas antigas
    tasks_to_remove = []
    for task_id, task in processing_tasks.items():
        if "created_at" in task and (current_time - task["created_at"]) > (max_age_hours * 3600):
            # Remover arquivos associados
            if "output_path" in task and os.path.exists(task["output_path"]):
                try:
                    os.remove(task["output_path"])
                    logger.info(f"Arquivo removido: {task['output_path']}")
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo: {task['output_path']}: {str(e)}")
            
            tasks_to_remove.append(task_id)
    
    # Remover tarefas do dicionário
    for task_id in tasks_to_remove:
        del processing_tasks[task_id]
        logger.info(f"Tarefa removida: {task_id}")
    
    # Limpar arquivos órfãos no diretório temporário
    files_removed = 0
    try:
        for filename in os.listdir(TEMP_VIDEO_DIR):
            file_path = os.path.join(TEMP_VIDEO_DIR, filename)
            file_age = os.path.getmtime(file_path)
            if (current_time - file_age) > (max_age_hours * 3600):
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        files_removed += 1
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo temporário {file_path}: {str(e)}")
        
        if files_removed > 0:
            logger.info(f"Limpeza concluída: {files_removed} arquivos removidos")
    except Exception as e:
        logger.error(f"Erro durante a limpeza de arquivos: {str(e)}")
    
    # Atualizar o tempo da última limpeza
    last_cleanup_time = current_time


def check_and_cleanup():
    """Verifica se é hora de executar a limpeza de arquivos."""
    current_time = time.time()
    
    # Executar limpeza se passou o intervalo definido desde a última limpeza
    if (current_time - last_cleanup_time) > CLEANUP_INTERVAL:
        logger.info("Iniciando limpeza automática de arquivos temporários...")
        cleanup_old_videos()
        return True
    
    return False


@router.get("/public-download/{video_id}")
@router.head("/public-download/{video_id}")
async def public_download_video(
    video_id: str,
    api_key: str = Security(api_key_query)
):
    """Endpoint público para download do vídeo processado usando token na URL."""
    # Verificar se o token é válido
    try:
        # Usar a mesma função de verificação de token do módulo de autenticação
        from bynnor_smart_monitoring.auth.auth import verify_token
        payload = verify_token(api_key)
        
        if not payload:
            logger.error(f"Token inválido ou expirado: {api_key[:10]}...")
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")
            
        # Extrair o user_id do campo correto no payload
        user_id = payload.get("user_id")
        if not user_id:
            logger.error(f"Token não contém user_id: {payload}")
            raise HTTPException(status_code=401, detail="Token inválido (sem user_id)")
            
        logger.info(f"Download público autorizado para o vídeo {video_id} pelo usuário {user_id}")
    except Exception as e:
        logger.error(f"Erro na autenticação via token URL: {str(e)}")
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    # Verificar se é hora de fazer limpeza
    check_and_cleanup()
    
    if video_id not in processing_tasks:
        logger.error(f"Vídeo {video_id} não encontrado nas tarefas de processamento")
        raise HTTPException(status_code=404, detail="Vídeo processado não encontrado")
    
    task = processing_tasks[video_id]
    logger.info(f"Tarefa encontrada para vídeo {video_id}: status={task['status']}")
    
    # Verificar se o usuário tem acesso a esta tarefa
    # Converter ambos para string para comparação segura
    task_user_id = str(task["user_id"])
    request_user_id = str(user_id)
    
    logger.info(f"Comparando user_id da tarefa ({task_user_id}) com user_id do token ({request_user_id})")
    
    if task_user_id != request_user_id:
        logger.error(f"Acesso negado: usuário {request_user_id} tentando acessar vídeo do usuário {task_user_id}")
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso")
    
    # Verificar se o processamento foi concluído
    if task["status"] != "completed":
        logger.error(f"Vídeo {video_id} não está pronto para download. Status atual: {task['status']}")
        raise HTTPException(
            status_code=400, 
            detail=f"O vídeo ainda não está pronto para download. Status atual: {task['status']}"
        )
    
    output_path = task["output_path"]
    logger.info(f"Caminho do arquivo para download público: {output_path}")
    
    if not os.path.exists(output_path):
        logger.error(f"Arquivo não encontrado no caminho: {output_path}")
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado no servidor")
    
    try:
        logger.info(f"Enviando arquivo {output_path} como resposta")
        
        # Usar o tipo de arquivo e nome específico solicitado
        file_ext = os.path.splitext(output_path)[1].lower()
        if file_ext == '.avi':
            media_type = "video/x-msvideo"
            filename = f"processed_video_{video_id}.avi"
        else:
            media_type = "video/mp4"
            filename = f"processed_video_{video_id}.mp4"
            
        logger.info(f"Tipo de mídia detectado: {media_type}, nome do arquivo: {filename}")
        
        # Adicionar cabeçalhos adicionais para melhorar a compatibilidade com navegadores
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        
        # Verificar se o arquivo existe e tem tamanho válido
        if os.path.getsize(output_path) == 0:
            logger.error(f"Arquivo vazio: {output_path}")
            raise HTTPException(status_code=500, detail="O arquivo de vídeo processado está vazio")
            
        return FileResponse(
            path=output_path, 
            filename=filename,
            media_type=media_type,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Erro ao enviar arquivo como resposta: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar arquivo: {str(e)}")

