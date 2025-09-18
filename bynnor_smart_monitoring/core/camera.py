import cv2
import time
import logging
import threading
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CameraConfig:
    """Configuração da câmera."""
    name: str
    rtsp_url: str
    width: int = 1280
    height: int = 720
    fps: int = 25
    reconnect_interval: int = 5  # segundos

class CameraStream:
    """Classe para gerenciar o fluxo de vídeo de uma câmera RTSP."""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.cap = None
        self.frame = None
        self.running = False
        self.thread = None
        self.callbacks = []
        self.connected = False
        
    def add_callback(self, callback: Callable):
        """Adiciona uma função de callback para processamento de frames."""
        self.callbacks.append(callback)
    
    def _connect(self) -> bool:
        """Estabelece conexão com a câmera."""
        try:
            logger.info(f"Conectando à câmera: {self.config.name} ({self.config.rtsp_url})")
            
            # Liberar qualquer cap existente antes de criar um novo
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
                logger.info(f"Liberando conexão anterior da câmera {self.config.name}")
                # Pequena pausa para garantir que os recursos sejam liberados
                time.sleep(0.5)
            
            # Verificar se é uma câmera local (índice numérico) ou RTSP (string)
            if isinstance(self.config.rtsp_url, int) or (isinstance(self.config.rtsp_url, str) and self.config.rtsp_url.isdigit()):
                # Câmera local - garantir que seja inteiro
                device_index = int(self.config.rtsp_url) if isinstance(self.config.rtsp_url, str) else self.config.rtsp_url
                logger.info(f"Tentando conectar à câmera local com índice {device_index}")
                
                # Tentar diferentes configurações para câmera local
                self.cap = cv2.VideoCapture(device_index)
                
                # Nota: CAP_PROP_BACKEND é somente leitura e não pode ser configurado
                # Apenas registrar o backend atual para fins de depuração
                if hasattr(cv2, 'CAP_PROP_BACKEND'):
                    backend = self.cap.get(cv2.CAP_PROP_BACKEND)
                    logger.info(f"Câmera local {device_index} usando backend {backend}")
            else:
                # Câmera RTSP - usar a URL como string
                logger.info(f"Tentando conectar à câmera RTSP com URL {self.config.rtsp_url}")
                self.cap = cv2.VideoCapture(self.config.rtsp_url)
            
            # Verificar se a câmera foi aberta com sucesso
            if not self.cap.isOpened():
                logger.error(f"Não foi possível abrir a câmera {self.config.name}")
                return False
                
            # Tentar ler um frame para confirmar que a câmera está funcionando
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                logger.error(f"Câmera {self.config.name} aberta, mas não retornou frame válido")
                self.cap.release()
                return False
                
            # Configurar propriedades da câmera
            logger.info(f"Configurando propriedades da câmera {self.config.name}: {self.config.width}x{self.config.height} @ {self.config.fps}fps")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Verificar se as configurações foram aplicadas
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            logger.info(f"Propriedades reais da câmera: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            if not self.cap.isOpened():
                logger.error(f"Não foi possível conectar à câmera: {self.config.name}")
                return False
                
            self.connected = True
            logger.info(f"Conexão estabelecida com sucesso: {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar à câmera {self.config.name}: {e}")
            return False
    
    def _process_frame(self, frame):
        """Processa o frame e chama os callbacks registrados."""
        if frame is None:
            return
            
        metadata = {
            "camera_name": self.config.name,
            "timestamp": time.time(),
            "width": frame.shape[1],
            "height": frame.shape[0]
        }
        
        for callback in self.callbacks:
            try:
                callback(frame.copy(), metadata)
            except Exception as e:
                logger.error(f"Erro no callback: {e}")
    
    def _run(self):
        """Loop principal de captura de frames."""
        frame_count = 0
        error_count = 0
        last_log_time = time.time()
        last_reconnect_time = 0
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        logger.info(f"Iniciando loop de captura para câmera {self.config.name} (URL: {self.config.rtsp_url})")
        
        while self.running:
            current_time = time.time()
            
            # Verificar se a câmera está conectada
            if not self.cap or not self.cap.isOpened():
                self.connected = False
                
                # Limitar tentativas de reconexão para evitar loops infinitos
                if current_time - last_reconnect_time < self.config.reconnect_interval:
                    time.sleep(0.5)  # Pequena pausa antes de tentar novamente
                    continue
                    
                last_reconnect_time = current_time
                reconnect_attempts += 1
                
                logger.warning(f"Câmera {self.config.name} não está aberta, tentativa de reconexão {reconnect_attempts}/{max_reconnect_attempts}")
                
                # Se exceder o número máximo de tentativas, aumentar o intervalo
                if reconnect_attempts > max_reconnect_attempts:
                    wait_time = self.config.reconnect_interval * 2
                    logger.error(f"Máximo de tentativas de reconexão excedido para câmera {self.config.name}, aguardando {wait_time}s")
                    time.sleep(wait_time)
                    reconnect_attempts = 0  # Resetar contador após espera longa
                    continue
                
                # Tentar reconectar
                if not self._connect():
                    logger.error(f"Falha ao reconectar à câmera {self.config.name}, tentando novamente em {self.config.reconnect_interval}s")
                    time.sleep(self.config.reconnect_interval)
                    continue
                else:
                    logger.info(f"Reconectado com sucesso à câmera {self.config.name}")
                    reconnect_attempts = 0  # Resetar contador após sucesso
                    error_count = 0
            
            # Tentar ler um frame
            try:
                # Verificar novamente se a câmera está aberta antes de tentar ler
                if not self.cap.isOpened():
                    logger.warning(f"Câmera {self.config.name} fechou inesperadamente")
                    self.connected = False
                    continue
                    
                ret, frame = self.cap.read()
                
                # Log periódico (a cada 5 segundos)
                if current_time - last_log_time > 5:
                    logger.info(f"Câmera {self.config.name}: {frame_count} frames capturados, {error_count} erros desde o último log")
                    frame_count = 0
                    error_count = 0
                    last_log_time = current_time
                
                if not ret or frame is None:
                    error_count += 1
                    logger.warning(f"Falha ao ler frame da câmera {self.config.name} (URL: {self.config.rtsp_url}), erro #{error_count}")
                    
                    # Se tivermos muitas falhas consecutivas, reconectar
                    if error_count > 5:  # Reduzido para 5 para reconectar mais rapidamente
                        logger.error(f"Muitas falhas consecutivas ({error_count}) na câmera {self.config.name}, reconectando...")
                        if self.cap:
                            self.cap.release()
                        self.connected = False
                        time.sleep(1)  # Pequena pausa antes de tentar reconectar
                        continue
                    
                    # Pequena pausa antes de tentar ler novamente
                    time.sleep(0.1)
                else:
                    # Frame capturado com sucesso
                    frame_count += 1
                    error_count = 0  # Resetar contador de erros
                    self.connected = True  # Confirmar que está conectado
                    
                    # Processar o frame capturado
                    self.frame = frame
                    self._process_frame(frame)
            except Exception as e:
                logger.error(f"Exceção ao ler frame da câmera {self.config.name}: {str(e)}")
                error_count += 1
                
                # Se tivermos muitas exceções consecutivas, reconectar
                if error_count > 3:
                    logger.error(f"Muitas exceções consecutivas na câmera {self.config.name}, reconectando...")
                    if self.cap:
                        self.cap.release()
                    self.connected = False
                continue
                
            # Pequena pausa para evitar uso excessivo da CPU
            time.sleep(0.01)
    
    def start(self) -> bool:
        """Inicia a captura de vídeo."""
        if self.running:
            logger.warning(f"A captura da câmera {self.config.name} já está em execução")
            return True
            
        if not self._connect():
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        logger.info(f"Captura de vídeo iniciada para a câmera {self.config.name}")
        return True
    
    def stop(self):
        """Para a captura de vídeo."""
        if not self.running:
            return
            
        logger.info(f"Parando captura de vídeo da câmera {self.config.name}")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5.0)
            
        if self.cap:
            self.cap.release()
            
        self.connected = False
    
    def get_frame(self):
        """Retorna o frame atual da câmera."""
        return self.frame
    
    def is_connected(self) -> bool:
        """Verifica se a câmera está conectada."""
        return self.connected

class CameraManager:
    """Gerenciador de múltiplas câmeras."""
    
    def __init__(self):
        self.cameras: Dict[str, CameraStream] = {}
    
    def add_camera(self, camera_id: str, name: str, rtsp_url: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Adiciona uma câmera ao gerenciador."""
        if camera_id in self.cameras:
            logger.warning(f"Câmera {camera_id} já existe")
            return False
            
        config = CameraConfig(name=name, rtsp_url=rtsp_url)
        camera = CameraStream(config)
        self.cameras[camera_id] = camera
        return True
    
    def remove_camera(self, camera_id: str) -> bool:
        """Remove uma câmera do gerenciador e libera todos os recursos associados.
        
        Args:
            camera_id: ID da câmera a ser removida
            
        Returns:
            bool: True se a câmera foi removida com sucesso, False caso contrário
        """
        try:
            if camera_id in self.cameras:
                logger.info(f"Iniciando remoção da câmera {camera_id}")
                camera = self.cameras[camera_id]
                
                # Parar a câmera se estiver em execução
                try:
                    if camera.is_running:
                        logger.info(f"Parando câmera {camera_id} que está em execução")
                        camera.stop()
                        # Aguardar um pouco para garantir que os recursos sejam liberados
                        time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Erro ao parar câmera {camera_id}: {str(e)}")
                
                # Limpar callbacks
                try:
                    if hasattr(camera, 'callbacks') and camera.callbacks:
                        logger.info(f"Limpando {len(camera.callbacks)} callbacks da câmera {camera_id}")
                        camera.callbacks.clear()
                except Exception as e:
                    logger.error(f"Erro ao limpar callbacks da câmera {camera_id}: {str(e)}")
                
                # Liberar recursos específicos da câmera local
                try:
                    if hasattr(camera, 'cap') and camera.cap is not None:
                        logger.info(f"Liberando recursos do VideoCapture para câmera {camera_id}")
                        camera.cap.release()
                        camera.cap = None
                except Exception as e:
                    logger.error(f"Erro ao liberar recursos do VideoCapture para câmera {camera_id}: {str(e)}")
                
                # Remover do dicionário
                del self.cameras[camera_id]
                logger.info(f"Câmera {camera_id} removida com sucesso")
                
                # Forçar coleta de lixo para liberar recursos
                import gc
                gc.collect()
                
                return True
            else:
                logger.warning(f"Tentativa de remover câmera inexistente: {camera_id}")
                return False
        except Exception as e:
            logger.error(f"Erro não tratado ao remover câmera {camera_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def start_camera(self, camera_id: str) -> bool:
        """Inicia uma câmera específica."""
        if camera_id not in self.cameras:
            return False
        return self.cameras[camera_id].start()
    
    def start_all(self) -> Dict[str, bool]:
        """Inicia todas as câmeras gerenciadas."""
        results = {}
        for camera_id, camera in self.cameras.items():
            results[camera_id] = camera.start()
        return results
    
    def stop_all(self):
        """Para todas as câmeras gerenciadas."""
        for camera in self.cameras.values():
            camera.stop()
            
    def stop_all_cameras(self):
        """Alias para stop_all() para compatibilidade com código existente."""
        self.stop_all()
    
    def get_camera(self, camera_id: str) -> Optional[CameraStream]:
        """Obtém uma câmera pelo ID."""
        return self.cameras.get(camera_id)
    
    def get_all_cameras(self) -> Dict[str, CameraStream]:
        """Retorna todas as câmeras gerenciadas."""
        return self.cameras
        
    def add_local_camera(self, camera_id: str = "local", name: str = "Câmera Local", device_index: int = 0) -> bool:
        """Adiciona a câmera local do notebook ao gerenciador.
        
        Args:
            camera_id: ID único para a câmera (padrão: 'local')
            name: Nome para exibição da câmera (padrão: 'Câmera Local')
            device_index: Índice do dispositivo de câmera (padrão: 0, primeira câmera)
            
        Returns:
            bool: True se a câmera foi adicionada com sucesso, False caso contrário
        """
        try:
            # Verificar se a câmera já existe e removê-la adequadamente
            if camera_id in self.cameras:
                logger.warning(f"Câmera {camera_id} já existe, removendo a antiga antes de adicionar nova")
                try:
                    # Remover câmera existente para evitar conflitos
                    self.remove_camera(camera_id)
                    # Pequena pausa para garantir que os recursos sejam liberados
                    time.sleep(1.0)
                except Exception as e:
                    logger.error(f"Erro ao remover câmera existente {camera_id}: {str(e)}")
                    # Continuar mesmo com erro, tentaremos substituir a câmera
            
            logger.info(f"Tentando adicionar câmera local com índice {device_index}")
            
            # Testar acesso à câmera diretamente para verificar se está disponível
            # Tentar diferentes índices se o fornecido não funcionar
            indices_to_try = [device_index]
            
            # Se o índice for 0, tentar também 1 e -1 como alternativas
            if device_index == 0:
                indices_to_try.extend([1, -1])
            
            success = False
            working_index = device_index
            test_cap = None
            frame = None
            width, height, fps = 640, 480, 30  # Valores padrão
            
            for idx in indices_to_try:
                logger.info(f"Tentando abrir câmera local com índice {idx}")
                
                # Liberar câmera anterior se existir
                if test_cap is not None:
                    try:
                        test_cap.release()
                        logger.info(f"Câmera de teste com índice anterior liberada")
                        time.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"Erro ao liberar câmera de teste anterior: {str(e)}")
                
                # Tentar abrir a câmera
                try:
                    test_cap = cv2.VideoCapture(idx)
                    
                    # Verificar se abriu
                    if not test_cap.isOpened():
                        logger.warning(f"Não foi possível abrir a câmera com índice {idx}")
                        continue
                    
                    # Tentar ler um frame
                    for attempt in range(3):  # Tentar até 3 vezes
                        ret, frame = test_cap.read()
                        if ret and frame is not None:
                            success = True
                            working_index = idx
                            
                            # Obter informações sobre a câmera
                            width = test_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                            height = test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                            fps = test_cap.get(cv2.CAP_PROP_FPS)
                            
                            logger.info(f"Câmera local detectada no índice {idx}: {width}x{height} @ {fps}fps")
                            break
                        else:
                            logger.warning(f"Tentativa {attempt+1} falhou ao ler frame da câmera {idx}")
                            time.sleep(0.5)
                    
                    if success:
                        break
                except Exception as e:
                    logger.warning(f"Erro ao testar câmera com índice {idx}: {str(e)}")
                    continue
            
            # Liberar a câmera de teste
            if test_cap is not None:
                try:
                    test_cap.release()
                    logger.info("Câmera de teste final liberada com sucesso")
                    # Pequena pausa para garantir que os recursos sejam liberados
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Erro ao liberar câmera de teste final: {str(e)}")
            
            if not success:
                logger.error("Não foi possível encontrar uma câmera local funcional")
                return False
            
            # Criar configuração com as propriedades detectadas e o índice que funcionou
            config = CameraConfig(
                name=f"{name} ({working_index})", 
                rtsp_url=str(working_index),  # Usar o índice que funcionou
                width=int(width) if width > 0 else 640,
                height=int(height) if height > 0 else 480,
                fps=int(fps) if fps > 0 else 30
            )
            
            # Criar e adicionar a câmera
            camera = CameraStream(config)
            self.cameras[camera_id] = camera
            logger.info(f"Câmera local adicionada com ID: {camera_id}, índice: {working_index}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar câmera local: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Garantir que qualquer recurso aberto seja liberado
            if 'test_cap' in locals() and test_cap is not None:
                try:
                    test_cap.release()
                except:
                    pass
            return False
