# realtime_rtsp_yolo_router.py
import os
import cv2
import time
import base64
import logging
import threading
import queue
import numpy as np
from typing import List, Optional, Dict
from db.base import SessionLocal


from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Body
from pydantic import BaseModel

# ========================= YOLO (Ultralytics) =================================
try:
    from ultralytics import YOLO
except Exception as e:
    raise RuntimeError("Instale o Ultralytics: pip install ultralytics") from e

# ========================= Auth/DB (stubs se não houver) ======================
try:
    from sqlalchemy.orm import Session  # type: ignore
except Exception:
    class Session:  # stub
        ...

try:
    from db.base import get_db  # type: ignore
except Exception:
    def get_db():
        return None

try:
    from models.models import User, UserRole  # type: ignore
except Exception:
    class UserRole:
        ADMIN = "ADMIN"
    class User:
        id: int = 1
        role: str = UserRole.ADMIN
        is_admin: bool = True

try:
    from bynnor_smart_monitoring.auth.auth import get_current_user, get_user_from_token  # type: ignore
except Exception:
    def get_current_user():
        return User()
    def get_user_from_token(token, db):
        return User()

# ========================= Logger/Router ======================================
logger = logging.getLogger("realtime")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s %(name)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

router = APIRouter()
realtime_sessions: Dict[str, "RealtimeSession"] = {}

# ========================= Detector ===========================================
class YoloDetector:
    def __init__(
        self,
        model_name: str = "yolov8n.pt",  # rápido e leve
        imgsz: int = 640,
        conf: float = 0.5,
        device: Optional[str] = None,
    ):
        self.model = YOLO(model_name)
        self.imgsz = imgsz
        self.conf = conf

        # Seleção de device
        self.device = device or ("cuda" if (hasattr(self.model, "device") and "cuda" in str(self.model.device)) else "cpu")
        try:
            self.model.to(self.device)
        except Exception:
            pass

        # Half-precision se CUDA
        if "cuda" in self.device:
            try:
                self.model.model.half()  # type: ignore[attr-defined]
                logger.info("YOLO em FP16 (half-precision) na GPU.")
            except Exception:
                logger.info("YOLO em FP32 (fallback).")

        logger.info(f"YOLO carregado | model={model_name} device={self.device} imgsz={imgsz} conf={conf}")

    def predict(self, frame_bgr: np.ndarray, classes: Optional[List[str]] = None):
        results = self.model.predict(
            source=frame_bgr,
            imgsz=self.imgsz,
            conf=self.conf,
            device=self.device,
            verbose=False
        )
        r = results[0]
        if classes:
            # Filtra por NOME de classe
            keep_idx = []
            all_cls = r.boxes.cls.int().tolist() if hasattr(r, "boxes") else []
            for i, cid in enumerate(all_cls):
                cname = r.names[cid]
                if cname in classes:
                    keep_idx.append(i)
            if keep_idx:
                r = r[keep_idx]  # type: ignore[index]
        return r

    @staticmethod
    def draw(result, frame: np.ndarray) -> np.ndarray:
        try:
            return result.plot()
        except Exception:
            return frame

# ========================= RTSP Reader ========================================
class RTSPCamera:
    """
    Captura RTSP com baixa latência:
    - Thread dedicada
    - Fila com maxsize=1 (mantém apenas o frame mais recente)
    - Dicas de buffering baixo
    """
    def __init__(self, camera_id: str, rtsp_url: str, width: int = 0, height: int = 0):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.width = width
        self.height = height

        self.cap = None
        self.running = False
        self.thread = None
        self.q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=1)

    def _open(self):
        url = self.rtsp_url
        # Força TCP quando possível (estabilidade/latência)
        if "rtsp://" in url and "rtsp_transport" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}rtsp_transport=tcp"

        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        if self.width > 0:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height > 0:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        if not self.cap.isOpened():
            raise RuntimeError(f"Falha ao abrir RTSP: {url}")

    def start(self):
        if self.running:
            return
        self._open()
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info(f"RTSP {self.camera_id} iniciado.")

    def _loop(self):
        last_log = time.time()
        while self.running:
            if not self.cap:
                break

            grabbed = self.cap.grab()
            if not grabbed:
                time.sleep(0.02)
                continue

            ok, frame = self.cap.retrieve()
            if not ok or frame is None:
                continue

            # Mantém somente o frame mais novo
            if not self.q.empty():
                try:
                    _ = self.q.get_nowait()
                except Exception:
                    pass
            try:
                self.q.put_nowait(frame)
            except Exception:
                pass

            if time.time() - last_log > 10:
                last_log = time.time()
                logger.debug(f"{self.camera_id} buffer size={self.q.qsize()}")

        self.stop()

    def read(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        # Primeiro marca como não rodando para interromper o loop
        self.running = False
        
        # Aguarda um pequeno tempo para garantir que o loop perceba a mudança
        time.sleep(0.05)
        
        # Limpa a fila para evitar referências pendentes
        try:
            while not self.q.empty():
                try:
                    _ = self.q.get_nowait()
                except Exception:
                    break
        except Exception:
            pass
            
        # Libera o objeto de captura com tratamento de erros
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                logger.warning(f"Erro ao liberar captura RTSP {self.camera_id}: {e}")
                
        # Garante que a referência seja removida
        self.cap = None
        
        # Aguarda a thread terminar se existir
        if self.thread and self.thread.is_alive() and threading.current_thread() != self.thread:
            try:
                self.thread.join(timeout=1.0)
            except Exception:
                pass
                
        self.thread = None
        logger.info(f"RTSP {self.camera_id} parado com sucesso.")

# ========================= Session ============================================
class RealtimeSession:
    def __init__(
        self,
        session_id: str,
        camera: RTSPCamera,
        detector: YoloDetector,
        classes: Optional[List[str]] = None,
        conf: float = 0.5,
        display_size=(640, 360),
    ):
        self.id = session_id
        self.camera = camera
        self.detector = detector
        self.classes = classes
        self.conf = conf
        self.display_size = display_size

        self.websockets: List[WebSocket] = []
        self.active = False

        self.infer_thread = None
        self.frame_lock = threading.Lock()
        self.last_jpeg: Optional[bytes] = None
        self.fps = 0.0

    def start(self):
        if self.active:
            return
        self.active = True
        self.camera.start()
        self.infer_thread = threading.Thread(target=self._infer_loop, daemon=True)
        self.infer_thread.start()
        logger.info(f"Sessão {self.id} iniciada.")

    def stop(self):
        # Primeiro desativa a flag para interromper o loop de inferência
        self.active = False
        
        # Aguarda um pequeno tempo para garantir que o loop de inferência perceba a mudança
        time.sleep(0.1)
        
        # Limpa a referência ao último frame JPEG para evitar problemas de memória
        with self.frame_lock:
            self.last_jpeg = None
            
        # Para a câmera de forma segura
        try:
            self.camera.stop()
        except Exception as e:
            logger.error(f"Erro ao parar câmera na sessão {self.id}: {e}")
            
        # Limpa a lista de websockets
        self.websockets.clear()
        
        logger.info(f"Sessão {self.id} parada com sucesso.")

    def set_config(self, classes: Optional[List[str]] = None, conf: Optional[float] = None):
        if classes is not None:
            self.classes = classes
        if conf is not None:
            import numpy as _np
            self.conf = float(_np.clip(conf, 0.05, 0.99))
            self.detector.conf = self.conf

    def _infer_loop(self):
        last_tick = time.time()
        while self.active:
            frame = self.camera.read(timeout=0.5)
            if frame is None:
                continue

            t0 = time.time()
            try:
                res = self.detector.predict(frame, self.classes)
                out = self.detector.draw(res, frame)
            except Exception as e:
                logger.warning(f"Falha YOLO: {e}")
                out = frame

            if self.display_size:
                try:
                    out = cv2.resize(out, self.display_size, interpolation=cv2.INTER_AREA)
                except Exception:
                    pass

            # Encode JPEG adaptativo
            try:
                ok, jpeg = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if not ok:
                    continue
                data = jpeg.tobytes()
                if len(data) > 500_000:
                    ok2, jpeg2 = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 55])
                    if ok2:
                        data = jpeg2.tobytes()
                with self.frame_lock:
                    self.last_jpeg = data
            except Exception:
                continue

            dt = time.time() - t0
            if time.time() - last_tick >= 1.0:
                self.fps = round(1.0 / max(dt, 1e-6), 1)
                last_tick = time.time()

    def add_ws(self, ws: WebSocket):
        self.websockets.append(ws)

    def remove_ws(self, ws: WebSocket):
        if ws in self.websockets:
            self.websockets.remove(ws)

    async def pump_ws(self, ws: WebSocket):
        try:
            await ws.accept()
            while self.active:
                with self.frame_lock:
                    data = self.last_jpeg
                if data:
                    b64 = base64.b64encode(data).decode("ascii")
                    await ws.send_json({"f": b64, "fps": self.fps, "sid": self.id, "t": int(time.time() * 1000)})
                await asyncio_sleep(0.033)  # ~30fps alvo
        except WebSocketDisconnect:
            self.remove_ws(ws)
        except Exception as e:
            logger.warning(f"WS erro: {e}")
            self.remove_ws(ws)

# ========================= Shim de Compatibilidade =============================
class RealtimeDetectionSession(RealtimeSession):
    """
    Compatibilidade para código legado que espera 'RealtimeDetectionSession'.
    Mantém add_websocket/remove_websocket e process_frame (modo push).
    """
    def __init__(
        self,
        camera_id: str,
        user_id: int,
        detector: YoloDetector = None,
        rtsp_url: str = None,
        classes: Optional[List[str]] = None,
        confidence: float = 0.5,
        display_size=(640, 360),
        width: int = 0,
        height: int = 0,
    ):
        self._push_mode = rtsp_url is None
        if detector is None:
            detector = YoloDetector(imgsz=640, conf=confidence)

        if self._push_mode:
            dummy = RTSPCamera(camera_id=camera_id, rtsp_url="rtsp://dummy")
            dummy.start = lambda: None  # type: ignore
            dummy.stop = lambda: None   # type: ignore
            dummy.read = lambda timeout=0.0: None  # type: ignore
            super().__init__(
                session_id=f"{camera_id}_{user_id}",
                camera=dummy,
                detector=detector,
                classes=classes,
                conf=confidence,
                display_size=display_size,
            )
            self.active = True
        else:
            cam = RTSPCamera(camera_id=camera_id, rtsp_url=rtsp_url, width=width, height=height)
            super().__init__(
                session_id=f"{camera_id}_{user_id}",
                camera=cam,
                detector=detector,
                classes=classes,
                conf=confidence,
                display_size=display_size,
            )
            self.start()

    # Nomes antigos
    def add_websocket(self, websocket: WebSocket):
        return self.add_ws(websocket)

    def remove_websocket(self, websocket: WebSocket):
        return super().remove_ws(websocket)

    def set_detection_config(self, classes: Optional[List[str]] = None, confidence: Optional[float] = None):
        return self.set_config(classes, confidence)

    def process_frame(self, frame, metadata=None):
        if not self.active or frame is None:
            return
        try:
            t0 = time.time()
            res = self.detector.predict(frame, self.classes)
            out = self.detector.draw(res, frame)
            if self.display_size:
                try:
                    out = cv2.resize(out, self.display_size, interpolation=cv2.INTER_AREA)
                except Exception:
                    pass
            ok, jpeg = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ok:
                return
            data = jpeg.tobytes()
            if len(data) > 500_000:
                ok2, jpeg2 = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 55])
                if ok2:
                    data = jpeg2.tobytes()
            with self.frame_lock:
                self.last_jpeg = data
            dt = time.time() - t0
            self.fps = round(1.0 / max(dt, 1e-6), 1)
        except Exception as e:
            logger.warning(f"process_frame falhou: {e}")

# ========================= Utils ==============================================
import asyncio
async def asyncio_sleep(s: float):
    await asyncio.sleep(s)

# ========================= Schemas (Opção B) ===================================
class StartCompatRequest(BaseModel):
    rtsp_url: str
    classes: Optional[List[str]] = None
    confidence: float = 0.5
    imgsz: int = 640
    width: int = 0       # forçar resolução de captura (opcional)
    height: int = 0
    display_w: int = 640
    display_h: int = 360
    model_name: str = "yolov8n.pt"
    device: Optional[str] = None  # "cuda" | "cpu"

class ConfigureRequest(BaseModel):
    classes: Optional[List[str]] = None
    confidence: Optional[float] = None

# ========================= Rotas (Opção B) ====================================
@router.post("/start/{camera_id}")
def start_realtime_detection_compat(
    camera_id: str,
    req: StartCompatRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Inicia sessão com URL antiga /start/{camera_id}
    - rtsp_url e demais configs no body
    """
    session_key = f"{camera_id}_{current_user.id}"
    if session_key in realtime_sessions:
        return {"status": "already_running", "session_id": session_key}

    cam = RTSPCamera(camera_id=camera_id, rtsp_url=req.rtsp_url, width=req.width, height=req.height)
    det = YoloDetector(model_name=req.model_name, imgsz=req.imgsz, conf=req.confidence, device=req.device)
    sess = RealtimeSession(
        session_id=session_key,
        camera=cam,
        detector=det,
        classes=req.classes,
        conf=req.confidence,
        display_size=(req.display_w, req.display_h),
    )
    realtime_sessions[session_key] = sess
    sess.start()
    return {"status": "started", "session_id": session_key}

@router.post("/stop/{session_id}")
def stop_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    # Verificar se a sessão existe
    if session_id not in realtime_sessions:
        return {"status": "not_found", "session_id": session_id}
    
    try:
        # Obter referência à sessão
        sess = realtime_sessions[session_id]
        
        # Remover do dicionário global primeiro para evitar novas referências
        # enquanto estamos parando
        realtime_sessions.pop(session_id, None)
        
        # Parar a sessão com tratamento de erros
        try:
            sess.stop()
        except Exception as e:
            logger.error(f"Erro ao parar sessão {session_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Forçar a liberação de memória
        import gc
        gc.collect()
        
        return {"status": "stopped", "session_id": session_id}
    except Exception as e:
        logger.error(f"Erro ao processar parada da sessão {session_id}: {e}")
        return {"status": "error", "session_id": session_id, "error": str(e)}


@router.post("/configure/{session_id}")
def configure_session(
    session_id: str,
    req: ConfigureRequest,
    current_user: User = Depends(get_current_user)
):
    if session_id not in realtime_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    sess = realtime_sessions[session_id]
    sess.set_config(req.classes, req.confidence)
    return {
        "status": "configured",
        "session_id": session_id,
        "classes": sess.classes,
        "confidence": sess.conf
    }

@router.websocket("/ws/{session_id}")
async def ws_stream(websocket: WebSocket, session_id: str, token: Optional[str] = None):
    if token is None:
        await websocket.close(code=1008, reason="Token não fornecido")
        return

    # aqui usamos SessionLocal direto
    db = SessionLocal()
    try:
        user = get_user_from_token(token, db)
        if not user:
            await websocket.close(code=1008, reason="Token inválido")
            return
    finally:
        db.close()

    if session_id not in realtime_sessions:
        await websocket.close(code=1008, reason="Sessão não encontrada")
        return

    sess = realtime_sessions[session_id]
    await sess.pump_ws(websocket)