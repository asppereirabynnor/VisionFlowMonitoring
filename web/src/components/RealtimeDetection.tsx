import React, { useState, useEffect, useRef } from 'react';
import { 
  Button, Card, Typography, Grid, Box, CircularProgress, Alert, Chip,
  Paper, IconButton, FormControlLabel, Switch, FormGroup, Select, MenuItem,
  InputLabel, FormControl
} from '@mui/material';
import { PlayArrow, Pause, Settings, Videocam, Cancel as CancelIcon } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../config';


// Constantes para Material UI

interface RTSPChannel {
  token: string;
  name: string;
  rtsp_url: string | null;
  resolution: string | null;
  encoding: string | null;
  framerate: number | null;
  bitrate: number | null;
}

interface RealtimeDetectionProps {
  cameraId: string;
  cameraName: string;
  allowLocalCamera?: boolean; // Propriedade opcional para permitir câmera local
}

// Interface Detection removida pois não é mais necessária

//const API_URL = process.env.REACT_APP_API_URL || '';

const RealtimeDetection: React.FC<RealtimeDetectionProps> = ({ cameraId, cameraName, allowLocalCamera = true }) => {
  const { token } = useAuth();
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState<number>(0);
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.5);
  const [availableClasses, setAvailableClasses] = useState<string[]>([
    'person', 'car', 'truck', 'bicycle', 'motorcycle', 'bus', 'dog', 'cat'
  ]);
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  
  // Estados para câmera local
  const [useLocalCamera, setUseLocalCamera] = useState<boolean>(false);
  const [deviceIndex, setDeviceIndex] = useState<number>(0);
  const [selectedDevice, setSelectedDevice] = useState<string>('0');
  const [availableDevices, setAvailableDevices] = useState<MediaDeviceInfo[]>([]);
  
  // Estados para canais RTSP
  const [rtspChannels, setRtspChannels] = useState<RTSPChannel[]>([]);
  const [selectedRtspChannel, setSelectedRtspChannel] = useState<string>('');
  const [loadingChannels, setLoadingChannels] = useState<boolean>(false);

  // Listar dispositivos de câmera disponíveis
  const listVideoDevices = async () => {
    try {
      // Verificar se o navegador suporta a API MediaDevices
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        console.error("Este navegador não suporta a API MediaDevices");
        return;
      }
      
      // Solicitar permissão para acessar dispositivos de mídia
      await navigator.mediaDevices.getUserMedia({ video: true });
      
      // Listar todos os dispositivos
      const devices = await navigator.mediaDevices.enumerateDevices();
      
      // Filtrar apenas dispositivos de vídeo
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      setAvailableDevices(videoDevices);
      
      // Se houver dispositivos, definir o primeiro como padrão
      if (videoDevices.length > 0) {
        setSelectedDevice('0'); // Usar o primeiro dispositivo como padrão
        setDeviceIndex(0);
      }
      
      console.log('Dispositivos de vídeo disponíveis:', videoDevices);
    } catch (err) {
      console.error('Erro ao listar dispositivos de vídeo:', err);
      setError('Não foi possível acessar as câmeras do dispositivo');
    }
  };
  
  // Função para buscar canais RTSP disponíveis
  const fetchRtspChannels = async () => {
    if (!cameraId || !token) return;
    
    try {
      setLoadingChannels(true);
      setError(null);
      
      const response = await fetch(`${API_URL}/onvif/cameras/${cameraId}/rtsp-channels`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao buscar canais RTSP');
      }
      
      const channels: RTSPChannel[] = await response.json();
      setRtspChannels(channels);
      
      // Selecionar o primeiro canal por padrão se houver canais disponíveis
      if (channels.length > 0 && !selectedRtspChannel) {
        setSelectedRtspChannel(channels[0].token);
      }
      
      console.log('Canais RTSP disponíveis:', channels);
    } catch (err: any) {
      console.error('Erro ao buscar canais RTSP:', err);
      setError(err.message || 'Erro ao buscar canais RTSP');
    } finally {
      setLoadingChannels(false);
    }
  };
  
  // Carregar dispositivos de vídeo e canais RTSP ao montar o componente
  useEffect(() => {
    if (allowLocalCamera) {
      listVideoDevices();
    }
    
    if (cameraId && !useLocalCamera) {
      fetchRtspChannels();
    }
  }, [allowLocalCamera, cameraId, token, useLocalCamera]);

  // Iniciar detecção em tempo real
  const startDetection = async () => {
    if ((!cameraId && !useLocalCamera) || !token) return;

    try {
      setLoading(true);
      setError(null);
      
      let response;
      
      if (useLocalCamera) {
        // Usar endpoint para câmera local
        const deviceIdx = parseInt(selectedDevice || '0');
        console.log(`Iniciando detecção com câmera local, índice: ${deviceIdx}`);
        
        response = await fetch(`${API_URL}/realtime-detection/start-local-camera`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            device_index: deviceIdx,
            classes: selectedClasses.length > 0 ? selectedClasses : null,
            confidence: confidenceThreshold
          })
        });
      } else {
        // Usar endpoint para câmera IP normal
        const requestBody: any = {
          classes: selectedClasses.length > 0 ? selectedClasses : null,
          confidence: confidenceThreshold
        };
        
        // Adicionar o canal RTSP selecionado, se houver
        if (selectedRtspChannel) {
          const channel = rtspChannels.find(ch => ch.token === selectedRtspChannel);
          if (channel && channel.rtsp_url) {
            requestBody.rtsp_url = channel.rtsp_url;
            console.log(`Usando canal RTSP: ${channel.name} (${channel.rtsp_url})`);
          }
        }
        
        response = await fetch(`${API_URL}/realtime-detection/start/${cameraId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(requestBody)
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao iniciar detecção em tempo real');
      }

      const data = await response.json();
      setSessionId(data.session_id);
      setIsDetecting(true);
      
      // As configurações já foram enviadas na requisição inicial
      console.log('Detecção iniciada com configurações:', {
        classes: selectedClasses.length > 0 ? selectedClasses : 'todas',
        confidence: confidenceThreshold
      });
      
      // Conectar ao WebSocket
      connectWebSocket(data.session_id);
    } catch (err: any) {
      console.error('Erro ao iniciar detecção em tempo real:', err);
      const errorMessage = err.message || 'Erro ao iniciar detecção';
      console.error('Mensagem de erro:', errorMessage);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Iniciar detecção com câmera local
  const startLocalCameraDetection = async () => {
    if (!useLocalCamera) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log(`Iniciando detecção com câmera local, índice: ${selectedDevice}`);
      
      const deviceIdx = parseInt(selectedDevice || '0');
      console.log(`Índice da câmera convertido para número: ${deviceIdx}`);
      
      const response = await fetch(`${API_URL}/realtime-detection/start-local-camera`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          device_index: deviceIdx,
          classes: selectedClasses.length > 0 ? selectedClasses : null,
          confidence: confidenceThreshold
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao iniciar detecção com câmera local');
      }
      
      const data = await response.json();
      console.log('Resposta do servidor:', data);
      
      const { session_id, camera_info } = data;
      setSessionId(session_id);
      setIsDetecting(true);
      
      // Log das informações da câmera
      if (camera_info) {
        console.log(`Câmera detectada: ${camera_info.width}x${camera_info.height} @ ${camera_info.fps}fps`);
      }
      
      // Conectar ao WebSocket
      console.log(`Conectando ao WebSocket com session_id: ${session_id}`);
      connectWebSocket(session_id);
    } catch (err: any) {
      console.error('Erro ao iniciar detecção com câmera local:', err);
      const errorMessage = err.message || 'Erro ao iniciar detecção com câmera local';
      console.error('Mensagem de erro:', errorMessage);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Parar detecção em tempo real
  const stopDetection = async () => {
    if (!sessionId || !token) return;

    try {
      setLoading(true);
      
      // Fechar WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const response = await fetch(`${API_URL}/realtime-detection/stop/${sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao parar detecção em tempo real');
      }

      setIsDetecting(false);
      setSessionId(null);
      setFps(0);
      
      // Limpar o canvas
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };

  // Configurar parâmetros de detecção
  const configureDetection = async (sid: string = sessionId || '') => {
    if (!sid || !token) return;

    try {
      const response = await fetch(`${API_URL}/realtime-detection/configure/${sid}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          classes: selectedClasses.length > 0 ? selectedClasses : null,
          confidence: confidenceThreshold
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao configurar detecção');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao configurar detecção');
    }
  };

  // Conectar ao WebSocket para receber frames e detecções
  const connectWebSocket = (sid: string) => {
    const wsUrl = `${API_URL.replace('http://', 'ws://').replace('https://', 'wss://')}/realtime-detection/ws/${sid}?token=${token}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket conectado');
    };

    ws.onmessage = (event) => {
      try {
        // Verificar se os dados recebidos são uma string
        if (typeof event.data !== 'string') {
          console.error('Dados do WebSocket não são uma string:', typeof event.data);
          return;
        }
        
        // Tentar fazer o parse do JSON com tratamento de erro
        let data;
        try {
          data = JSON.parse(event.data);
        } catch (parseError) {
          console.error('Erro ao fazer parse dos dados do WebSocket:', parseError);
          return;
        }
        
        // Verificar se os dados são válidos
        if (!data || typeof data !== 'object') {
          console.error('Dados do WebSocket inválidos ou vazios');
          return;
        }
        
        // Usar os nomes de campos abreviados do backend otimizado
        const cameraId = data.c || data.camera_id;
        const frameData = data.f || data.frame;
        const timestamp = data.t || (data.timestamp ? data.timestamp * 1000 : Date.now());
        
        // Verificar se o frame é válido e é uma string
        if (!frameData || typeof frameData !== 'string') {
          console.error('Frame inválido ou não é uma string');
          return;
        }
        
        // Log para depuração
        console.log(`Recebido frame de ${frameData.length} caracteres, FPS: ${data.fps || 0}`);
        
        // Atualizar FPS e outras informações de estado
        setFps(data.fps || 0);
        
        // Desenhar o frame no canvas (as detecções já estão desenhadas no frame pelo backend)
        drawFrame(frameData);
      } catch (err) {
        console.error('Erro ao processar mensagem do WebSocket:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('Erro no WebSocket:', error);
      setError('Erro na conexão de streaming');
    };

    ws.onclose = () => {
      console.log('WebSocket desconectado');
      if (isDetecting) {
        // Tentar reconectar se a detecção ainda estiver ativa
        setTimeout(() => {
          if (isDetecting && sessionId) {
            connectWebSocket(sessionId);
          }
        }, 2000);
      }
    };
  };

  // Funções calculateIoU e applyNonMaxSuppression removidas pois não são mais utilizadas
  
  /**
   * Desenha o frame recebido do backend no canvas.
   * 
   * IMPORTANTE: As detecções já são desenhadas no backend (em realtime_detection.py)
   * e enviadas como parte do frame processado. O frontend apenas exibe o frame
   * sem fazer nenhum processamento adicional de detecções.
   * 
   * Esta abordagem elimina a sobreposição de quadros de detecção que ocorria
   * quando tanto o backend quanto o frontend desenhavam os quadros.
   */
  const drawFrame = (frameData: string | undefined) => {
    // Validação básica do frame
    if (typeof frameData !== 'string' || frameData.length < 100) {
      console.error(`Frame inválido: ${frameData ? frameData.length : 'undefined'} caracteres`);
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas || !canvas.getContext) {
      console.error('Canvas não disponível');
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      console.error('Contexto 2D não disponível');
      return;
    }

    try {
      // Verificar se os dados estão em formato base64 ou hex
      let imageUrl: string;
      
      // Verificar se é base64 válido (caracteres base64 típicos)
      // Melhorar a detecção de base64 para aceitar qualquer caractere válido em base64
      if (frameData.match(/^[A-Za-z0-9+/=]+$/)) {
        console.log('Processando frame como base64');
        // Base64: criar URL diretamente
        imageUrl = `data:image/jpeg;base64,${frameData}`;
      } else {
        console.log('Processando frame como hexadecimal');
        // Formato antigo (hex): converter para bytes
        try {
          const hexMatches = frameData.match(/.{1,2}/g);
          if (!hexMatches) {
            console.error('Formato hexadecimal inválido');
            return;
          }
          
          const frameBytes = new Uint8Array(hexMatches.map(byte => parseInt(byte, 16)));
          if (frameBytes.length < 50) {
            console.error(`Frame hexadecimal muito pequeno: ${frameBytes.length} bytes`);
            return;
          }
          
          // Criar blob e URL da imagem
          const blob = new Blob([frameBytes], { type: 'image/jpeg' });
          if (blob.size === 0) {
            console.error('Blob vazio criado');
            return;
          }
          
          imageUrl = URL.createObjectURL(blob);
        } catch (e) {
          console.error('Erro ao processar frame hexadecimal:', e);
          return;
        }
      }
      
      // Carregar e desenhar a imagem
      const img = new Image();
      
      // Definir timeout curto para evitar bloqueio se a imagem não carregar
      const imageTimeout = setTimeout(() => {
        if (imageUrl.startsWith('blob:')) {
          URL.revokeObjectURL(imageUrl);
        }
      }, 1000);
      
      img.onload = () => {
        clearTimeout(imageTimeout);
        
        // Limpar canvas antes de desenhar
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Desenhar imagem no canvas
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        // Liberar URL para evitar vazamento de memória
        if (imageUrl.startsWith('blob:')) {
          URL.revokeObjectURL(imageUrl);
        }
      };
      
      img.onerror = () => {
        clearTimeout(imageTimeout);
        if (imageUrl.startsWith('blob:')) {
          URL.revokeObjectURL(imageUrl);
        }
      };
      
      // Definir prioridade alta para carregamento da imagem
      img.decoding = 'sync';
      // A propriedade importance não existe no tipo HTMLImageElement
      
      // Iniciar carregamento da imagem
      img.src = imageUrl;
    } catch (e) {
      // Silenciar erros para evitar spam no console
    }
  };
  
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (sessionId) {
        stopDetection();
      }
    };
  }, []);

  // Aplicar configurações quando alteradas
  useEffect(() => {
    if (isDetecting && sessionId) {
      configureDetection();
    }
  }, [selectedClasses, confidenceThreshold]);

  return (
    <Paper style={{ padding: '8px', marginBottom: '8px', backgroundColor: 'transparent', boxShadow: 'none' }}>
      {/* Título opcional - pode ser exibido ou não dependendo do contexto */}
      {false && (
        <Typography variant="h6" style={{ marginBottom: '16px' }}>
          Detecção em Tempo Real - {useLocalCamera ? 'Câmera Local' : cameraName}
        </Typography>
      )}
      
      <div style={{ 
        position: 'relative', 
        width: '100%', 
        height: '100%',
        textAlign: 'center', 
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center'
      }}>
        <canvas 
          ref={canvasRef} 
          style={{ 
            maxWidth: '100%', 
            maxHeight: '100%',
            width: 'auto',
            height: 'auto', 
            objectFit: 'contain',
            backgroundColor: '#000'
          }}
          width={640}
          height={360}
        />
        
        {loading && (
          <div style={{ 
            position: 'absolute', 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.5)'
          }}>
            <CircularProgress color="primary" />
          </div>
        )}
      </div>
      
      <div style={{ 
        position: 'absolute', 
        bottom: '16px', 
        left: '16px', 
        right: '16px', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        zIndex: 10
      }}>
        {error && (
          <Alert 
            severity="error" 
            style={{ 
              position: 'absolute', 
              bottom: '70px', 
              left: '16px', 
              right: '16px',
              opacity: 0.9
            }}
          >
            {error}
          </Alert>
        )}
        
        {/* Controles principais */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button
            variant="contained"
            color="primary"
            size="small"
            startIcon={isDetecting ? <Pause /> : <PlayArrow />}
            onClick={isDetecting ? stopDetection : (useLocalCamera ? startLocalCameraDetection : startDetection)}
            disabled={loading || (!cameraId && !useLocalCamera)}
            style={{ 
              backgroundColor: isDetecting ? 'rgba(211, 47, 47, 0.8)' : 'rgba(25, 118, 210, 0.8)',
              backdropFilter: 'blur(4px)'
            }}
          >
            {isDetecting ? 'Parar' : 'Iniciar'}
          </Button>
          
          <Button
            variant="outlined"
            size="small"
            startIcon={<Settings />}
            onClick={() => setShowSettings(!showSettings)}
            style={{ 
              borderColor: 'rgba(255, 255, 255, 0.3)', 
              color: 'white',
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              backdropFilter: 'blur(4px)'
            }}
          >
            Configurações
          </Button>
        </div>
        
        {/* Indicadores */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {isDetecting && (
            <Chip 
              label={`FPS: ${fps.toFixed(1)}`} 
              color="success" 
              variant="outlined" 
              size="small"
              style={{ 
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                backdropFilter: 'blur(4px)',
                border: '1px solid rgba(76, 175, 80, 0.5)'
              }}
            />
          )}
          
          {allowLocalCamera && (
            <Chip
              label={useLocalCamera ? 'Câmera Local' : 'Câmera IP'}
              color="info"
              variant="outlined"
              size="small"
              style={{ 
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                backdropFilter: 'blur(4px)',
                border: '1px solid rgba(33, 150, 243, 0.5)'
              }}
              onClick={() => !isDetecting && setUseLocalCamera(!useLocalCamera)}
            />
          )}
        </div>
      </div>
      
      {/* Configurações de câmera local - exibidas apenas quando necessário */}
      {/* Configurações de câmera local - exibidas apenas quando necessário */}
      {allowLocalCamera && useLocalCamera && !isDetecting && (
        <Paper 
          variant="outlined" 
          style={{ 
            padding: '12px', 
            position: 'absolute',
            bottom: '70px',
            left: '16px',
            right: '16px',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            zIndex: 10
          }}
        >
          {availableDevices.length > 0 && (
            <FormControl fullWidth size="small">
              <InputLabel id="camera-device-label" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                Dispositivo de câmera
              </InputLabel>
              <Select
                labelId="camera-device-label"
                value={selectedDevice}
                label="Dispositivo de câmera"
                onChange={(e) => setSelectedDevice(String(e.target.value))}
                disabled={isDetecting}
                style={{ color: 'white' }}
              >
                {availableDevices.map((device, index) => (
                  <MenuItem key={device.deviceId} value={String(index)}>
                    {device.label || `Câmera ${index + 1}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Paper>
      )}
      
      {/* Seleção de canais RTSP - exibida apenas quando necessário */}
      {!useLocalCamera && rtspChannels.length > 0 && !isDetecting && (
        <Paper 
          variant="outlined" 
          style={{ 
            padding: '12px', 
            position: 'absolute',
            bottom: '70px',
            left: '16px',
            right: '16px',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            zIndex: 10
          }}
        >
          <FormControl fullWidth size="small">
            <InputLabel id="rtsp-channel-label" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Canal RTSP
            </InputLabel>
            <Select
              labelId="rtsp-channel-label"
              value={selectedRtspChannel}
              label="Canal RTSP"
              onChange={(e) => setSelectedRtspChannel(String(e.target.value))}
              disabled={isDetecting || loadingChannels}
              style={{ color: 'white' }}
            >
              {rtspChannels.map((channel) => (
                <MenuItem key={channel.token} value={channel.token}>
                  {channel.name} {channel.resolution ? `(${channel.resolution})` : ''}
                </MenuItem>
              ))}
            </Select>
            
            {loadingChannels && (
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                <CircularProgress size={16} sx={{ mr: 1 }} />
                <Typography variant="caption" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                  Carregando canais disponíveis...
                </Typography>
              </Box>
            )}
            
            {selectedRtspChannel && (
              <Box sx={{ mt: 1 }}>
                {(() => {
                  const channel = rtspChannels.find(ch => ch.token === selectedRtspChannel);
                  if (channel) {
                    return (
                      <Typography variant="caption" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                        {channel.encoding && `Codec: ${channel.encoding}`}
                        {channel.framerate && ` | FPS: ${channel.framerate}`}
                        {channel.bitrate && ` | Bitrate: ${channel.bitrate / 1000}kbps`}
                      </Typography>
                    );
                  }
                  return null;
                })()}
              </Box>
            )}
          </FormControl>
          
          <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-end' }}>
            <Button 
              size="small" 
              onClick={fetchRtspChannels}
              disabled={loadingChannels}
              style={{ 
                color: 'rgba(33, 150, 243, 0.9)',
                textTransform: 'none'
              }}
            >
              Atualizar canais
            </Button>
          </Box>
        </Paper>
      )}
      
      {showSettings && (
        <Paper 
          variant="outlined" 
          style={{ 
            padding: '16px', 
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '80%',
            maxWidth: '500px',
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            zIndex: 20,
            color: 'white'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <Typography variant="subtitle1" style={{ color: 'white' }}>
              Configurações de Detecção
            </Typography>
            <IconButton 
              size="small" 
              onClick={() => setShowSettings(false)}
              style={{ color: 'rgba(255, 255, 255, 0.7)' }}
            >
              <CancelIcon fontSize="small" />
            </IconButton>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <Typography variant="body2" style={{ color: 'rgba(255, 255, 255, 0.7)' }} gutterBottom>
                Classes para detectar:
              </Typography>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px' }}>
                {availableClasses.map((cls) => (
                  <Chip
                    key={cls}
                    label={cls}
                    color={selectedClasses.includes(cls) ? "primary" : "default"}
                    size="small"
                    onClick={() => {
                      if (selectedClasses.includes(cls)) {
                        setSelectedClasses(selectedClasses.filter(c => c !== cls));
                      } else {
                        setSelectedClasses([...selectedClasses, cls]);
                      }
                    }}
                    style={{ 
                      margin: '2px',
                      backgroundColor: selectedClasses.includes(cls) 
                        ? 'rgba(25, 118, 210, 0.7)' 
                        : 'rgba(255, 255, 255, 0.1)',
                      color: selectedClasses.includes(cls) ? 'white' : 'rgba(255, 255, 255, 0.8)',
                      borderColor: selectedClasses.includes(cls) 
                        ? 'rgba(25, 118, 210, 0.9)' 
                        : 'rgba(255, 255, 255, 0.3)'
                    }}
                  />
                ))}
              </div>
            </div>
            
            <div>
              <Typography variant="body2" style={{ color: 'rgba(255, 255, 255, 0.7)' }} gutterBottom>
                Limiar de confiança: {(confidenceThreshold * 100).toFixed(0)}%
              </Typography>
              <div style={{ padding: '0 10px' }}>
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button 
                variant="contained" 
                color="primary"
                size="small"
                onClick={() => {
                  if (isDetecting && sessionId) {
                    configureDetection();
                  }
                  setShowSettings(false);
                }}
                style={{ 
                  backgroundColor: 'rgba(25, 118, 210, 0.8)',
                  backdropFilter: 'blur(4px)'
                }}
              >
                Aplicar
              </Button>
            </div>
          </div>
        </Paper>
      )}
    </Paper>
  );
};

export default RealtimeDetection;
