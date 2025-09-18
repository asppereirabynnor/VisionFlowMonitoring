import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

import zeep
from onvif import ONVIFCamera, exceptions
from zeep.exceptions import Fault

logger = logging.getLogger(__name__)

@dataclass
class ONVIFConfig:
    """Configuração para conexão ONVIF."""
    ip: str
    port: int = 80  # Porta padrão para serviços ONVIF é geralmente 80
    username: str = ""
    password: str = ""
    wsdl_path: str = ""
    
    def get_xaddr(self) -> str:
        """Retorna o endereço ONVIF completo."""
        return f"http://{self.ip}:{self.port}/onvif/device_service"

@dataclass
class PTZPosition:
    """Representa uma posição PTZ (Pan-Tilt-Zoom)."""
    pan: float = 0.0
    tilt: float = 0.0
    zoom: float = 0.0
    preset_token: str = ""
    name: str = ""

class ONVIFController:
    """Controlador ONVIF para câmeras IP."""
    
    def __init__(self, config: ONVIFConfig):
        self.config = config
        self.connected = False
        self.cam = None
        self.media_service = None
        self.ptz_service = None
        self.imaging_service = None
        self.device_service = None
        logger.info(f"Inicializando controlador ONVIF para {self.config.ip}:{self.config.port}")
        
    def connect(self) -> bool:
        """Conecta com a câmera via ONVIF."""
        try:
            logger.info(f"Conectando à câmera ONVIF: {self.config.ip}:{self.config.port}")
            
            # Determinar o caminho WSDL
            wsdl_path = self.config.wsdl_path
            
            # Verificar se o caminho WSDL foi especificado e existe
            if wsdl_path and os.path.exists(wsdl_path):
                logger.info(f"Usando caminho WSDL personalizado: {wsdl_path}")
            else:
                # Não especificar o caminho WSDL, deixando a biblioteca usar o padrão interno
                wsdl_path = ''
                logger.info("Usando caminho WSDL padrão da biblioteca")
                
            logger.info(f"Self Data : {self.config.ip} : {self.config.port} : {self.config.username} : {self.config.password}")  

            # Garantir que todos os parâmetros sejam do tipo correto
            ip = str(self.config.ip) if self.config.ip else ""
            port = int(self.config.port) if self.config.port else 80
            username = str(self.config.username) if self.config.username else ""
            password = str(self.config.password) if self.config.password else ""
            
            # Verificar se o IP é válido
            if not ip:
                raise ValueError("Endereço IP da câmera não pode ser vazio")
                
            logger.info(f"Conectando com parâmetros validados: IP={ip}, Porta={port}, Usuário={'*' * len(username) if username else 'None'}")
            
            # Criar instância da câmera ONVIF
            try:
                # Primeiro, tente sem especificar o caminho WSDL
                if not wsdl_path:
                    logger.info("Tentando conexão sem especificar WSDL")
                    self.cam = ONVIFCamera(
                        ip,
                        port,
                        username,
                        password
                    )
                else:
                    # Se tiver um caminho WSDL, use-o
                    logger.info(f"Tentando conexão com WSDL: {wsdl_path}")
                    self.cam = ONVIFCamera(
                        ip,
                        port,
                        username,
                        password,
                        wsdl_path
                    )
            except Exception as e:
                # Se falhar, tente com o caminho WSDL vazio
                logger.warning(f"Falha na primeira tentativa de conexão: {e}. Tentando abordagem alternativa...")
                try:
                    self.cam = ONVIFCamera(
                        ip,
                        port,
                        username,
                        password,
                        ''
                    )
                except Exception as e2:
                    logger.error(f"Falha na segunda tentativa de conexão: {e2}")
                    raise e2
            
            # Inicializar serviços
            self.device_service = self.cam.create_devicemgmt_service()
            
            # Considerar conectado se conseguiu criar o serviço de dispositivo
            if self.device_service is not None:
                self.connected = True
                logger.info(f"Conexão ONVIF estabelecida com sucesso: {self.config.ip}")
                
                # Tentar obter informações do dispositivo, mas não falhar se não conseguir
                try:
                    device_info = self.device_service.GetDeviceInformation()
                    logger.info(f"Tipo de resposta GetDeviceInformation: {type(device_info)}")
                    
                    # Verificar se device_info é um objeto válido
                    if device_info is not None:
                        # Converter para dicionário se tiver atributos
                        info_dict = {}
                        
                        # Tentar acessar atributos comuns
                        for attr in ['Manufacturer', 'Model', 'FirmwareVersion', 'SerialNumber', 'HardwareId']:
                            try:
                                if hasattr(device_info, attr):
                                    info_dict[attr] = getattr(device_info, attr)
                            except Exception as e:
                                logger.debug(f"Não foi possível acessar atributo {attr}: {e}")
                        
                        logger.info(f"Informações do dispositivo: {info_dict}")
                    else:
                        logger.warning("GetDeviceInformation retornou None")
                except Exception as e:
                    logger.warning(f"Não foi possível obter informações do dispositivo: {e}")
                    # Não falhar a conexão por causa disso
                    pass
                
                # Inicializar outros serviços conforme necessário
                try:
                    self.media_service = self.cam.create_media_service()
                except (exceptions.ONVIFError, Fault) as e:
                    logger.warning(f"Não foi possível criar serviço de mídia: {e}")
                    
                try:
                    self.ptz_service = self.cam.create_ptz_service()
                except (exceptions.ONVIFError, Fault) as e:
                    logger.warning(f"Não foi possível criar serviço PTZ: {e}")
                    
                try:
                    self.imaging_service = self.cam.create_imaging_service()
                except (exceptions.ONVIFError, Fault) as e:
                    logger.warning(f"Não foi possível criar serviço de imagem: {e}")
                
                return True
            else:
                logger.error(f"Falha ao conectar à câmera ONVIF {self.config.ip}: Não foi possível obter informações do dispositivo")
                self.connected = False
                return False
                
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao conectar à câmera {self.config.ip}: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Erro ao conectar à câmera ONVIF {self.config.ip}: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta da câmera."""
        logger.info(f"Desconectando da câmera ONVIF: {self.config.ip}")
        self.connected = False
    
    def get_device_info(self) -> Dict[str, str]:
        """
        Obtém informações do dispositivo ONVIF.
        
        Returns:
            Dicionário com informações do dispositivo
        """
        if not self.connected or not self.device_service:
            logger.error("Não conectado à câmera ou serviço de dispositivo não disponível")
            return {}
            
        try:
            # Obter informações do dispositivo
            device_info = self.device_service.GetDeviceInformation()
            logger.debug(f"Tipo de resposta GetDeviceInformation: {type(device_info)}")
            
            # Inicializar dicionário de resultado
            result = {}
            
            # Tentar extrair informações de diferentes maneiras
            # Método 1: Tentar acessar como atributos do objeto
            for attr in ['Manufacturer', 'Model', 'FirmwareVersion', 'SerialNumber', 'HardwareId']:
                try:
                    if hasattr(device_info, attr):
                        result[attr] = getattr(device_info, attr)
                except Exception:
                    pass
            
            # Método 2: Tentar acessar como dicionário
            if not result and hasattr(device_info, 'get'):
                for key in ['Manufacturer', 'Model', 'FirmwareVersion', 'SerialNumber', 'HardwareId']:
                    try:
                        value = device_info.get(key, "")
                        if value:
                            result[key] = value
                    except Exception:
                        pass
            
            # Método 3: Tentar converter para string e extrair informações
            if not result:
                try:
                    info_str = str(device_info)
                    logger.debug(f"Informações do dispositivo como string: {info_str}")
                    # Preencher com informações básicas se não conseguir extrair
                    result = {
                        "Manufacturer": "Desconhecido",
                        "Model": "Desconhecido",
                        "FirmwareVersion": "Desconhecido",
                        "SerialNumber": "Desconhecido",
                        "HardwareId": "Desconhecido"
                    }
                except Exception:
                    pass
            
            # Garantir que temos pelo menos um dicionário vazio
            if not result:
                result = {
                    "Manufacturer": "",
                    "Model": "",
                    "FirmwareVersion": "",
                    "SerialNumber": "",
                    "HardwareId": ""
                }
            
            logger.info(f"Informações do dispositivo obtidas: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao obter informações do dispositivo: {e}")
            return {}
    
    def get_ptz_position(self) -> Optional[PTZPosition]:
        """Obtém a posição PTZ atual da câmera."""
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return None
            
        try:
            # Obter perfis de mídia
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return None
                else:
                    logger.error("Serviço de mídia não disponível")
                    return None
            
            # Obter status PTZ atual
            status = self.ptz_service.GetStatus({'ProfileToken': self.media_profile.token})
            
            # Extrair posição
            position = status.Position
            
            # Converter para nosso formato
            ptz_position = PTZPosition(
                pan=float(position.PanTilt.x) if hasattr(position, 'PanTilt') and hasattr(position.PanTilt, 'x') else 0.0,
                tilt=float(position.PanTilt.y) if hasattr(position, 'PanTilt') and hasattr(position.PanTilt, 'y') else 0.0,
                zoom=float(position.Zoom.x) if hasattr(position, 'Zoom') and hasattr(position.Zoom, 'x') else 0.0
            )
            
            logger.info(f"Posição PTZ obtida: pan={ptz_position.pan}, tilt={ptz_position.tilt}, zoom={ptz_position.zoom}")
            return ptz_position
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao obter posição PTZ: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao obter posição PTZ: {e}")
            return None
    
    def move_continuous(self, pan_speed: float, tilt_speed: float, zoom_speed: float = 0.0) -> bool:
        """
        Realiza movimento contínuo da câmera.
        
        Args:
            pan_speed: Velocidade de pan (-1.0 a 1.0)
            tilt_speed: Velocidade de tilt (-1.0 a 1.0)
            zoom_speed: Velocidade de zoom (-1.0 a 1.0)
            
        Returns:
            True se o comando foi executado com sucesso
        """
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return False
            
        try:
            # Obter perfil de mídia se ainda não tiver
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return False
                else:
                    logger.error("Serviço de mídia não disponível")
                    return False
            
            # Limita os valores ao intervalo [-1.0, 1.0]
            pan_speed = max(-1.0, min(1.0, pan_speed))
            tilt_speed = max(-1.0, min(1.0, tilt_speed))
            zoom_speed = max(-1.0, min(1.0, zoom_speed))
            
            # Criar objeto de velocidade
            velocity = {
                'PanTilt': {'x': pan_speed, 'y': tilt_speed},
                'Zoom': {'x': zoom_speed}
            }
            
            # Enviar comando de movimento contínuo
            request = {
                'ProfileToken': self.media_profile.token,
                'Velocity': velocity,
                'Timeout': 60  # Timeout em segundos
            }
            
            self.ptz_service.ContinuousMove(request)
            logger.info(f"Movimento contínuo iniciado: pan={pan_speed}, tilt={tilt_speed}, zoom={zoom_speed}")
            return True
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao mover câmera: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao mover câmera: {e}")
            return False
    
    def stop_movement(self) -> bool:
        """Para todos os movimentos da câmera."""
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return False
            
        try:
            # Obter perfil de mídia se ainda não tiver
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return False
                else:
                    logger.error("Serviço de mídia não disponível")
                    return False
            
            # Enviar comando de parada
            request = {'ProfileToken': self.media_profile.token}
            self.ptz_service.Stop(request)
            
            logger.info("Movimento da câmera parado com sucesso")
            return True
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao parar movimento da câmera: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao parar movimento da câmera: {e}")
            return False
    
    def move_absolute(self, position: PTZPosition) -> bool:
        """
        Move a câmera para uma posição absoluta.
        
        Args:
            position: Posição PTZ de destino
            
        Returns:
            True se o comando foi executado com sucesso
        """
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return False
            
        try:
            # Obter perfil de mídia se ainda não tiver
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return False
                else:
                    logger.error("Serviço de mídia não disponível")
                    return False
            
            # Criar objeto de posição
            pos = {
                'PanTilt': {'x': position.pan, 'y': position.tilt},
                'Zoom': {'x': position.zoom}
            }
            
            # Enviar comando de movimento absoluto
            request = {
                'ProfileToken': self.media_profile.token,
                'Position': pos,
                'Speed': {'PanTilt': {'x': 1.0, 'y': 1.0}, 'Zoom': {'x': 1.0}}  # Velocidade máxima
            }
            
            self.ptz_service.AbsoluteMove(request)
            logger.info(f"Movimento para posição absoluta iniciado: pan={position.pan}, tilt={position.tilt}, zoom={position.zoom}")
            return True
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao mover câmera para posição absoluta: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao mover câmera para posição absoluta: {e}")
            return False
    
    def get_presets(self) -> List[PTZPosition]:
        """Obtém a lista de presets da câmera."""
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return []
            
        try:
            # Obter perfil de mídia se ainda não tiver
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return []
                else:
                    logger.error("Serviço de mídia não disponível")
                    return []
            
            # Obter presets da câmera
            presets_dict = self.ptz_service.GetPresets({'ProfileToken': self.media_profile.token})
            
            # Converter para nossa estrutura
            result = []
            for token, preset in presets_dict.items():
                # Tentar obter a posição do preset
                position = PTZPosition(
                    preset_token=token,
                    name=preset.get('Name', f'Preset {token}')
                )
                
                # Adicionar à lista de resultados
                result.append(position)
                
            logger.info(f"Obtidos {len(result)} presets da câmera")
            return result
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao obter presets: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro ao obter presets: {e}")
            return []
    
    def go_to_preset(self, preset_token: str, speed: float = 1.0) -> bool:
        """
        Move a câmera para um preset específico.
        
        Args:
            preset_token: Token do preset
            speed: Velocidade do movimento (0.0 a 1.0)
            
        Returns:
            True se o comando foi executado com sucesso
        """
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return False
            
        try:
            # Obter perfil de mídia se ainda não tiver
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return False
                else:
                    logger.error("Serviço de mídia não disponível")
                    return False
            
            # Limita a velocidade ao intervalo [0.0, 1.0]
            speed = max(0.0, min(1.0, speed))
            
            # Criar objeto de velocidade
            speed_obj = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            # Enviar comando para ir para o preset
            request = {
                'ProfileToken': self.media_profile.token,
                'PresetToken': preset_token,
                'Speed': speed_obj
            }
            
            self.ptz_service.GotoPreset(request)
            logger.info(f"Movimento para preset {preset_token} iniciado com velocidade {speed}")
            return True
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao mover para preset {preset_token}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao mover para preset {preset_token}: {e}")
            return False
    
    def set_preset(self, name: str) -> Optional[str]:
        """
        Define um novo preset na posição atual da câmera.
        
        Args:
            name: Nome do preset
            
        Returns:
            Token do preset criado ou None em caso de erro
        """
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return None
            
        try:
            # Obter perfil de mídia se ainda não tiver
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return None
                else:
                    logger.error("Serviço de mídia não disponível")
                    return None
            
            # Criar o preset na posição atual
            request = {
                'ProfileToken': self.media_profile.token,
                'PresetName': name
            }
            
            # Algumas câmeras retornam o token diretamente, outras retornam um objeto
            result = self.ptz_service.SetPreset(request)
            
            # Extrair o token do resultado
            token = None
            if isinstance(result, str):
                token = result
            elif hasattr(result, 'PresetToken'):
                token = result.PresetToken
            else:
                # Tentar obter todos os presets e encontrar o que acabamos de criar
                presets = self.get_presets()
                for preset in presets:
                    if preset.name == name:
                        token = preset.preset_token
                        break
            
            if token:
                logger.info(f"Preset '{name}' criado com token {token}")
                return token
            else:
                logger.error(f"Não foi possível obter o token do preset '{name}' criado")
                return None
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao definir preset '{name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao definir preset '{name}': {e}")
            return None
    
    def remove_preset(self, preset_token: str) -> bool:
        """
        Remove um preset existente da câmera.
        
        Args:
            preset_token: Token do preset a ser removido
            
        Returns:
            True se o preset foi removido com sucesso
        """
        if not self.connected or not self.ptz_service:
            logger.error("Não conectado à câmera ou serviço PTZ não disponível")
            return False
            
        try:
            # Obter perfil de mídia se ainda não tiver
            if not hasattr(self, 'media_profile') or not self.media_profile:
                if self.media_service:
                    profiles = self.media_service.GetProfiles()
                    if profiles:
                        self.media_profile = profiles[0]  # Usar o primeiro perfil
                    else:
                        logger.error("Nenhum perfil de mídia encontrado")
                        return False
                else:
                    logger.error("Serviço de mídia não disponível")
                    return False
            
            # Remover o preset
            request = {
                'ProfileToken': self.media_profile.token,
                'PresetToken': preset_token
            }
            
            self.ptz_service.RemovePreset(request)
            logger.info(f"Preset {preset_token} removido com sucesso")
            return True
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao remover preset {preset_token}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao remover preset {preset_token}: {e}")
            return False
    
    def get_capabilities(self) -> Dict[str, bool]:
        """
        Obtém as capacidades ONVIF reais da câmera.
        
        Returns:
            Dicionário com as capacidades disponíveis
        """
        if not self.connected or not self.device_service:
            logger.error("Não conectado à câmera ou serviço de dispositivo não disponível")
            return {}
            
        try:
            # Obter capacidades reais da câmera
            capabilities = self.device_service.GetCapabilities()
            
            # Verificar quais serviços estão disponíveis
            result = {
                'ptz': hasattr(capabilities, 'PTZ') and capabilities.PTZ is not None,
                'imaging': hasattr(capabilities, 'Imaging') and capabilities.Imaging is not None,
                'media': hasattr(capabilities, 'Media') and capabilities.Media is not None,
                'events': hasattr(capabilities, 'Events') and capabilities.Events is not None,
                'analytics': hasattr(capabilities, 'Analytics') and capabilities.Analytics is not None,
                'device': hasattr(capabilities, 'Device') and capabilities.Device is not None,
            }
            
            logger.info(f"Capacidades da câmera obtidas: {result}")
            return result
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao obter capacidades: {e}")
            return {}
        except Exception as e:
            logger.error(f"Erro ao obter capacidades: {e}")
            return {}
    
    def get_rtsp_channels(self) -> List[Dict[str, Any]]:
        """
        Obtém os canais RTSP disponíveis na câmera.
        
        Returns:
            Lista de canais RTSP disponíveis com suas URLs e informações
        """
        if not self.connected or not self.media_service:
            logger.error("Não conectado à câmera ou serviço de mídia não disponível")
            return []
            
        try:
            # Obter perfis de mídia
            profiles = self.media_service.GetProfiles()
            if not profiles:
                logger.warning("Nenhum perfil de mídia encontrado na câmera")
                return []
                
            # Armazenar o primeiro perfil para uso em outras funções
            if not hasattr(self, 'media_profile') or not self.media_profile:
                self.media_profile = profiles[0]
                
            # Processar cada perfil para obter as URLs RTSP
            result = []
            for profile in profiles:
                try:
                    # Obter token do perfil
                    token = profile.token
                    
                    # Obter URI de streaming
                    stream_setup = {
                        'Stream': 'RTP-Unicast',
                        'Transport': {
                            'Protocol': 'RTSP'
                        }
                    }
                    
                    # Obter URI RTSP
                    uri_info = self.media_service.GetStreamUri({
                        'ProfileToken': token,
                        'StreamSetup': stream_setup
                    })
                    
                    # Obter a URL RTSP
                    rtsp_url = uri_info.Uri if hasattr(uri_info, 'Uri') else None
                    
                    # Adicionar credenciais à URL RTSP se necessário
                    if rtsp_url and self.config.username and self.config.password:
                        rtsp_parts = rtsp_url.split("://")
                        if len(rtsp_parts) > 1 and '@' not in rtsp_parts[1]:
                            rtsp_url = f"{rtsp_parts[0]}://{self.config.username}:{self.config.password}@{rtsp_parts[1]}"
                            logger.debug(f"Credenciais adicionadas à URL RTSP do perfil {token}")
                    
                    # Extrair informações do perfil
                    profile_info = {
                        'token': token,
                        'name': profile.Name if hasattr(profile, 'Name') else f"Profile {token}",
                        'rtsp_url': rtsp_url,
                        'resolution': None,
                        'encoding': None,
                        'framerate': None,
                        'bitrate': None
                    }
                    
                    # Tentar obter configurações de vídeo
                    try:
                        if hasattr(profile, 'VideoEncoderConfiguration') and profile.VideoEncoderConfiguration:
                            video_config = profile.VideoEncoderConfiguration
                            
                            # Resolução
                            if hasattr(video_config, 'Resolution'):
                                width = getattr(video_config.Resolution, 'Width', 0)
                                height = getattr(video_config.Resolution, 'Height', 0)
                                profile_info['resolution'] = f"{width}x{height}"
                            
                            # Encoding
                            if hasattr(video_config, 'Encoding'):
                                profile_info['encoding'] = video_config.Encoding
                            
                            # Framerate
                            if hasattr(video_config, 'RateControl') and hasattr(video_config.RateControl, 'FrameRateLimit'):
                                profile_info['framerate'] = video_config.RateControl.FrameRateLimit
                            
                            # Bitrate
                            if hasattr(video_config, 'RateControl') and hasattr(video_config.RateControl, 'BitrateLimit'):
                                profile_info['bitrate'] = video_config.RateControl.BitrateLimit
                    except Exception as e:
                        logger.warning(f"Erro ao obter configurações de vídeo para perfil {token}: {e}")
                    
                    # Adicionar à lista de resultados
                    result.append(profile_info)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar perfil {profile.token if hasattr(profile, 'token') else 'desconhecido'}: {e}")
            
            logger.info(f"Obtidos {len(result)} canais RTSP da câmera")
            return result
            
        except exceptions.ONVIFError as e:
            logger.error(f"Erro ONVIF ao obter canais RTSP: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro ao obter canais RTSP: {e}")
            return []
    
    @staticmethod
    def discover_devices(timeout: int = 5) -> List[Dict[str, Any]]:
        """
        Descobre dispositivos ONVIF na rede usando WS-Discovery.
        
        Args:
            timeout: Tempo limite em segundos para a descoberta
            
        Returns:
            Lista de dispositivos encontrados
        """
        try:
            from onvif import ONVIFCamera
            from onvif.discovery import WSDiscovery
            
            logger.info(f"Iniciando descoberta de dispositivos ONVIF na rede (timeout: {timeout}s)...")
            
            # Iniciar descoberta WS-Discovery
            wsd = WSDiscovery()
            wsd.start()
            
            # Procurar dispositivos ONVIF
            devices = wsd.searchServices(timeout=timeout)
            
            # Parar a descoberta
            wsd.stop()
            
            # Processar resultados
            result = []
            for device in devices:
                # Filtrar apenas dispositivos ONVIF
                if any('onvif' in scope.lower() for scope in device.getScopes()):
                    device_info = {
                        'address': device.getXAddrs()[0] if device.getXAddrs() else '',
                        'types': device.getTypes()[0] if device.getTypes() else '',
                        'scopes': [scope for scope in device.getScopes()]
                    }
                    
                    # Extrair informações adicionais dos escopos
                    for scope in device.getScopes():
                        if 'name/' in scope.lower():
                            device_info['name'] = scope.split('/')[-1]
                        elif 'hardware/' in scope.lower():
                            device_info['hardware'] = scope.split('/')[-1]
                    
                    result.append(device_info)
            
            logger.info(f"Descoberta concluída: {len(result)} dispositivos ONVIF encontrados")
            return result
            
        except ImportError as e:
            logger.error(f"Erro ao importar módulos de descoberta ONVIF: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro ao descobrir dispositivos ONVIF: {e}")
            return []
