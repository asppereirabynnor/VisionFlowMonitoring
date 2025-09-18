import React, { useState, useEffect } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import RealtimeDetection from '../components/RealtimeDetection';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  Tab,
  Tabs,
  Tooltip,
  Typography,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  useTheme,
  alpha,
  Alert,
  InputAdornment,
  Skeleton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Switch,
  FormControlLabel,
  Snackbar,
  SnackbarContent,
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  ArrowUpward,
  ArrowDownward,
  ArrowBack,
  ArrowForward,
  Add as AddIcon,
  ZoomIn,
  ZoomOut,
  Stop,
  Delete as DeleteIcon,
  Videocam as VideocamIcon,
  Settings as SettingsIcon,
  Bookmark as BookmarkIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Save as SaveIcon,
  PlayArrow as PlayArrowIcon,
  LocationOn as LocationIcon,
  Memory as MemoryIcon,
  ArrowBack as ArrowBackIcon,
  SportsEsports as SimulationIcon,
  CameraAlt as CameraAltIcon,
  Fullscreen as FullscreenIcon,
  PanTool as PanToolIcon,
  Notifications as NotificationsIcon,
  Image as ImageIcon,
  VideoLibrary as VideoLibraryIcon,
  Assessment as AssessmentIcon,
  Mic as MicIcon,
  Warning as WarningIcon,
  Router as RouterIcon,
  SettingsEthernet as SettingsEthernetIcon,
  Person as PersonIcon,
  LocationOn as LocationOnIcon,
  Business as BusinessIcon,
  Devices as DevicesIcon,
  SystemUpdateAlt as SystemUpdateAltIcon,
  VpnKey as VpnKeyIcon,
  Badge as BadgeIcon,
} from '@mui/icons-material';
import StopIcon from '@mui/icons-material/Stop';
import {
  getCamera,
  getDeviceInfo,
  getCapabilities,
  getCameraPresets,
  createPreset,
  gotoPreset,
  deletePreset,
  controlPTZ,
  stopPTZ,
  updateCameraScreenshot,
  CameraPreset,
} from '../services/cameraService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`camera-tabpanel-${index}`}
      aria-labelledby={`camera-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const CameraDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const cameraId = parseInt(id || '0');
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [openPresetDialog, setOpenPresetDialog] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [presetDescription, setPresetDescription] = useState('');
  
  // Estados para o upload de imagem
  const [imageBase64, setImageBase64] = useState<string>('');
  const [previewImage, setPreviewImage] = useState<string>('');
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [uploadMessage, setUploadMessage] = useState<string>('');

  // Estados para o processamento de vídeo
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [processingVideo, setProcessingVideo] = useState<boolean>(false);
  const [processedFrame, setProcessedFrame] = useState<string>('');
  const [videoProcessingError, setVideoProcessingError] = useState<string>('');
  const [detectedObjects, setDetectedObjects] = useState<Array<{class_name: string, confidence: number}>>([]);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);

  // Queries
  const { data: camera, isLoading: cameraLoading } = useQuery({
    queryKey: ['camera', cameraId],
    queryFn: () => getCamera(cameraId),
    enabled: !!cameraId,
  });

  const { data: deviceInfo, isLoading: deviceInfoLoading } = useQuery({
    queryKey: ['deviceInfo', cameraId],
    queryFn: () => getDeviceInfo(cameraId),
    enabled: !!cameraId,
  });

  const { data: capabilities, isLoading: capabilitiesLoading } = useQuery({
    queryKey: ['capabilities', cameraId],
    queryFn: () => getCapabilities(cameraId),
    enabled: !!cameraId,
  });

  const { data: presets, isLoading: presetsLoading } = useQuery({
    queryKey: ['presets', cameraId],
    queryFn: () => getCameraPresets(cameraId),
    enabled: !!cameraId,
  });

  // Mutations
  const createPresetMutation = useMutation(
    (data: { name: string; description?: string }) =>
      createPreset(cameraId, data.name, data.description),
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['presets', cameraId] });
        setOpenPresetDialog(false);
        setPresetName('');
        setPresetDescription('');
      },
    }
  );

  const gotoPresetMutation = useMutation(
    (presetId: number) => gotoPreset(cameraId, presetId)
  );

  const deletePresetMutation = useMutation(
    (presetId: number) => deletePreset(cameraId, presetId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['presets', cameraId] });
      },
    }
  );

  const ptzMutation = useMutation(
    (params: { cameraId: number; pan: number; tilt: number; zoom: number; mode: 'continuous' | 'absolute' | 'relative' | 'stop' }) => 
      controlPTZ(params.cameraId, { pan: params.pan, tilt: params.tilt, zoom: params.zoom, mode: params.mode })
  );

  const stopPTZMutation = useMutation(
    () => stopPTZ(cameraId)
  );

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleOpenPresetDialog = () => {
    setOpenPresetDialog(true);
  };

  const handleClosePresetDialog = () => {
    setOpenPresetDialog(false);
    setPresetName('');
    setPresetDescription('');
  };
  
  // Função para manipular o upload de imagem
  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Verificar o tipo e tamanho do arquivo
    if (!file.type.match('image.*')) {
      setUploadStatus('error');
      setUploadMessage('Por favor, selecione apenas arquivos de imagem.');
      return;
    }
    
    if (file.size > 5 * 1024 * 1024) { // 5MB
      setUploadStatus('error');
      setUploadMessage('A imagem deve ter no máximo 5MB.');
      return;
    }
    
    setUploadStatus('loading');
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setPreviewImage(result);
      setImageBase64(result);
      setUploadStatus('success');
      setUploadMessage('Imagem carregada com sucesso!');
    };
    
    reader.onerror = () => {
      setUploadStatus('error');
      setUploadMessage('Erro ao processar a imagem.');
    };
    
    reader.readAsDataURL(file);
  };
  
  // Função para salvar a imagem no banco de dados
  const handleSaveScreenshot = async () => {
    if (!imageBase64 || !cameraId) {
      console.error('Faltando imageBase64 ou cameraId', { imageBase64: !!imageBase64, cameraId });
      return;
    }
    
    console.log('Iniciando salvamento do screenshot para câmera ID:', cameraId);
    setUploadStatus('loading');
    
    try {
      // Chamada para a API para salvar o screenshot
      console.log('Enviando screenshot para a API...');
      const response = await updateCameraScreenshot(cameraId, imageBase64);
      console.log('Resposta da API:', response);
      
      setUploadStatus('success');
      setUploadMessage('Screenshot salvo com sucesso!');
      
      // Limpar o cache para forçar a atualização da lista de câmeras
      console.log('Invalidando cache de queries...');
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
      queryClient.invalidateQueries({ queryKey: ['camera', cameraId] });
    } catch (error: any) {
      setUploadStatus('error');
      setUploadMessage(`Erro ao salvar o screenshot: ${error?.message || 'Erro desconhecido'}`);
      console.error('Erro ao salvar screenshot:', error);
    }
  };
  
  // Função para iniciar o processamento de vídeo com YOLO
  const handleProcessVideo = () => {
    if (!videoUrl || !cameraId) {
      setVideoProcessingError('URL de vídeo inválida ou ID da câmera não disponível');
      return;
    }
    
    setProcessingVideo(true);
    setProcessedFrame('');
    setDetectedObjects([]);
    setVideoProcessingError('');
    
    try {
      // Criar conexão WebSocket
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Obter o token JWT do localStorage
      const token = localStorage.getItem('token');
      
      if (!token) {
        setVideoProcessingError('Usuário não autenticado. Faça login novamente.');
        setProcessingVideo(false);
        return;
      }
      
      // Incluir o token como query parameter
      const wsUrl = `${wsProtocol}//localhost:8000/video-processing/${cameraId}?token=${token}`;
      
      console.log(`Conectando ao WebSocket: ${wsUrl.substring(0, wsUrl.indexOf('?') + 15)}...`);
      const ws = new WebSocket(wsUrl);
      setWebsocket(ws);
      
      ws.onopen = () => {
        console.log('Conexão WebSocket estabelecida');
        setVideoProcessingError('');
        // Iniciar o carregamento do vídeo
        initVideoProcessing(videoUrl, ws);
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.processed_frame) {
          setProcessedFrame(data.processed_frame);
        }
        if (data.detections) {
          setDetectedObjects(data.detections);
        }
        if (data.error) {
          setVideoProcessingError(data.error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('Erro na conexão WebSocket:', error);
        setVideoProcessingError('Erro na conexão com o servidor de processamento. Verifique se o servidor está em execução na porta 8000.');
        setProcessingVideo(false);
        setWebsocket(null);
      };
      
      ws.onclose = (event) => {
        console.log('Conexão WebSocket fechada', event.code, event.reason);
        setProcessingVideo(false);
        setWebsocket(null);
        
        // Se não foi um fechamento normal (código 1000), mostrar erro
        if (event.code !== 1000) {
          setVideoProcessingError(`Conexão encerrada inesperadamente (código ${event.code})`);
        }
      };
      
    } catch (error: any) {
      console.error('Erro ao iniciar processamento de vídeo:', error);
      setVideoProcessingError(`Erro ao iniciar processamento: ${error?.message || 'Erro desconhecido'}`);
      setProcessingVideo(false);
    }
  };
  
  // Função para iniciar o processamento do vídeo
  const initVideoProcessing = (url: string, ws: WebSocket) => {
    try {
      // Criar um elemento de vídeo para carregar o vídeo
      const video = document.createElement('video');
      video.crossOrigin = 'anonymous';
      video.src = url;
      video.muted = true;
      
      // Configurar o canvas para capturar frames
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      video.onloadedmetadata = () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        video.play();
        
        // Enviar frames para o servidor a cada 100ms
        const interval = setInterval(() => {
          if (!ws || ws.readyState !== WebSocket.OPEN || !processingVideo) {
            clearInterval(interval);
            return;
          }
          
          if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const frame = canvas.toDataURL('image/jpeg', 0.8);
            ws.send(JSON.stringify({ frame }));
          }
        }, 100);
        
        // Limpar o intervalo quando o vídeo terminar
        video.onended = () => {
          clearInterval(interval);
          setProcessingVideo(false);
        };
      };
      
      video.onerror = () => {
        setVideoProcessingError('Erro ao carregar o vídeo. Verifique a URL e tente novamente.');
        setProcessingVideo(false);
      };
      
    } catch (error: any) {
      console.error('Erro ao processar vídeo:', error);
      setVideoProcessingError(`Erro ao processar vídeo: ${error?.message || 'Erro desconhecido'}`);
      setProcessingVideo(false);
    }
  };
  
  // Função para parar o processamento de vídeo
  const handleStopProcessing = () => {
    if (websocket) {
      websocket.close();
      setWebsocket(null);
    }
    setProcessingVideo(false);
  };
  
  // Limpar recursos ao desmontar o componente
  useEffect(() => {
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [websocket]);

  const handleCreatePreset = () => {
    if (presetName) {
      createPresetMutation.mutate({
        name: presetName,
        description: presetDescription || undefined,
      });
    }
  };

  const handleGotoPreset = (presetId: number) => {
    gotoPresetMutation.mutate(presetId);
  };

  const handleDeletePreset = (presetId: number) => {
    if (window.confirm('Tem certeza que deseja excluir este preset?')) {
      deletePresetMutation.mutate(presetId);
    }
  };

  const handlePTZControl = (pan: number, tilt: number, zoom: number) => {
    ptzMutation.mutate({
      cameraId,
      pan,
      tilt,
      zoom,
      mode: 'continuous',
    });
  };

  const handleStopPTZ = () => {
    stopPTZMutation.mutate();
  };

  const isLoading = cameraLoading || deviceInfoLoading || capabilitiesLoading || presetsLoading;
  const hasPTZ = capabilities?.ptz;

  const theme = useTheme();
  const navigate = useNavigate();
  
  return (
    <Box sx={{ flexGrow: 1 }}>
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Box sx={{ mb: 4 }}>
            <Button 
              startIcon={<ArrowBackIcon />} 
              onClick={() => navigate('/cameras')}
              sx={{ mb: 2 }}
            >
              Voltar para lista
            </Button>
            
            <Paper 
              elevation={0} 
              sx={{ 
                p: 3, 
                borderRadius: 2,
                background: `linear-gradient(135deg, ${theme.palette.primary.dark}, ${theme.palette.primary.main})`,
                color: 'white',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              <Box sx={{ 
                position: 'absolute', 
                top: 0, 
                right: 0, 
                width: '40%', 
                height: '100%', 
                opacity: 0.1,
                background: 'url("/camera-pattern.png") no-repeat right center',
                backgroundSize: 'cover',
                zIndex: 0
              }} />
              
              <Box sx={{ position: 'relative', zIndex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <VideocamIcon sx={{ mr: 1 }} />
                  <Typography variant="h4" fontWeight="500">
                    {camera?.name}
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <LocationIcon fontSize="small" />
                  <Typography variant="body1">
                    {camera?.location || 'Sem localização definida'}
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                  <Chip 
                    label={camera?.is_active ? 'Online' : 'Offline'} 
                    size="small" 
                    color={camera?.is_active ? 'success' : 'error'}
                    icon={camera?.is_active ? <CheckCircleIcon /> : <CancelIcon />}
                  />
                  {hasPTZ && (
                    <Chip 
                      label="PTZ" 
                      size="small" 
                      color="info" 
                      icon={<SettingsIcon />}
                    />
                  )}
                </Box>
              </Box>
            </Paper>
          </Box>

          <Paper sx={{ borderRadius: 2, mb: 3, overflow: 'hidden' }}>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              variant="scrollable"
              scrollButtons="auto"
              sx={{
                '& .MuiTab-root': {
                  minHeight: 48,
                  py: 1.5,
                  px: 2,
                  borderRadius: '8px 8px 0 0',
                  '&.Mui-selected': {
                    color: 'primary.main',
                    fontWeight: 'medium',
                    backgroundColor: alpha(theme.palette.primary.main, 0.08),
                  },
                },
              }}
            >
              <Tab icon={<VideocamIcon />} label="Visualização" iconPosition="start" />
              <Tab icon={<SettingsIcon />} label="Controle PTZ" iconPosition="start" disabled={!hasPTZ} />
              <Tab icon={<BookmarkIcon />} label="Presets" iconPosition="start" disabled={!hasPTZ} />
              <Tab icon={<InfoIcon />} label="Informações" iconPosition="start" />
              <Tab icon={<SimulationIcon />} label="Simulação" iconPosition="start" />
              <Tab icon={<AssessmentIcon />} label="Detecção em Tempo Real" iconPosition="start" />
            </Tabs>
          </Paper>

          {/* Tab de Detecção em Tempo Real */}
          <TabPanel value={tabValue} index={5}>
            {camera && (
              <RealtimeDetection cameraId={cameraId.toString()} cameraName={camera.name} />
            )}
          </TabPanel>

          {/* Tab de Visualização */}
          <TabPanel value={tabValue} index={0}>
            <Card elevation={3} sx={{ borderRadius: 2, overflow: 'hidden' }}>
              <Box sx={{ position: 'relative' }}>
                <Paper
                  sx={{
                    minHeight: 500,
                    bgcolor: '#111',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    overflow: 'hidden',
                    borderRadius: 0
                  }}
                >
                  {/* Efeito de grade tecnológica */}
                  <Box sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundImage: `linear-gradient(rgba(0, 0, 0, 0) 95%, ${alpha(theme.palette.primary.main, 0.3)} 100%), 
                                      linear-gradient(90deg, rgba(0, 0, 0, 0) 95%, ${alpha(theme.palette.primary.main, 0.3)} 100%)`,
                    backgroundSize: '20px 20px',
                    opacity: 0.4,
                    zIndex: 1
                  }} />
                  
                  {/* Overlay de interface tecnológica */}
                  <Box sx={{
                    position: 'absolute',
                    top: 16,
                    left: 16,
                    zIndex: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}>
                    <Chip 
                      label="LIVE" 
                      size="small" 
                      color="error" 
                      sx={{ 
                        borderRadius: '4px',
                        '& .MuiChip-label': { px: 1 },
                        animation: 'pulse 1.5s infinite'
                      }}
                    />
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                      {new Date().toLocaleTimeString()}
                    </Typography>
                  </Box>
                  
                  <Box sx={{
                    position: 'absolute',
                    top: 16,
                    right: 16,
                    zIndex: 2
                  }}>
                    <Chip 
                      label={camera?.name} 
                      size="small" 
                      sx={{ 
                        bgcolor: 'rgba(0,0,0,0.5)', 
                        color: 'white',
                        borderRadius: '4px'
                      }}
                      icon={<VideocamIcon sx={{ color: 'white !important', fontSize: '0.8rem' }} />}
                    />
                  </Box>
                  
                  <Box sx={{
                    position: 'absolute',
                    bottom: 16,
                    left: 16,
                    zIndex: 2
                  }}>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                      {camera?.location || 'Localização não definida'}
                    </Typography>
                  </Box>
                  
                  {/* Componente de detecção em tempo real */}
                  {camera && (
                    <Box sx={{ width: '100%', height: '100%', zIndex: 2 }}>
                      <RealtimeDetection 
                        cameraId={cameraId.toString()} 
                        cameraName={camera.name} 
                      />
                    </Box>
                  )}
                </Paper>
                
                {/* Controles de vídeo */}
                <Paper sx={{ 
                  p: 1, 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  bgcolor: alpha(theme.palette.primary.main, 0.05),
                  borderTop: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
                }}>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="Iniciar/Parar detecção">
                      <IconButton size="small">
                        <PlayArrowIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Capturar imagem">
                      <IconButton size="small">
                        <CameraAltIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                  
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="Tela cheia">
                      <IconButton size="small">
                        <FullscreenIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Configurações de detecção">
                      <IconButton size="small">
                        <SettingsIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Paper>
              </Box>
            </Card>
          </TabPanel>

          {/* Tab de Controle PTZ */}
          <TabPanel value={tabValue} index={1}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={7}>
                <Card elevation={3} sx={{ 
                  borderRadius: 2, 
                  overflow: 'hidden',
                  background: `linear-gradient(to bottom, ${alpha(theme.palette.background.paper, 0.8)}, ${theme.palette.background.paper})`,
                  backdropFilter: 'blur(10px)',
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
                }}>
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <SettingsIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
                      <Typography variant="h6" fontWeight="500">
                        Controle de Movimento
                      </Typography>
                    </Box>
                    
                    <Box sx={{ 
                      position: 'relative',
                      width: '100%',
                      height: 280,
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      mt: 2,
                      mb: 1
                    }}>
                      {/* Círculo de fundo */}
                      <Box sx={{
                        position: 'absolute',
                        width: 220,
                        height: 220,
                        borderRadius: '50%',
                        border: `2px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                        boxShadow: `0 0 15px ${alpha(theme.palette.primary.main, 0.1)}`,
                        background: `radial-gradient(circle, ${alpha(theme.palette.primary.main, 0.05)} 0%, ${alpha(theme.palette.background.paper, 0.8)} 70%)`,
                      }} />
                      
                      {/* Linhas de grade */}
                      <Box sx={{
                        position: 'absolute',
                        width: 220,
                        height: 220,
                        borderRadius: '50%',
                        '&::before': {
                          content: '""',
                          position: 'absolute',
                          top: '50%',
                          left: 0,
                          right: 0,
                          height: '1px',
                          backgroundColor: alpha(theme.palette.primary.main, 0.2),
                        },
                        '&::after': {
                          content: '""',
                          position: 'absolute',
                          left: '50%',
                          top: 0,
                          bottom: 0,
                          width: '1px',
                          backgroundColor: alpha(theme.palette.primary.main, 0.2),
                        }
                      }} />
                      
                      {/* Botão central */}
                      <Tooltip title="Parar movimento">
                        <IconButton 
                          onClick={handleStopPTZ}
                          sx={{ 
                            position: 'absolute',
                            zIndex: 2,
                            bgcolor: alpha(theme.palette.error.main, 0.1),
                            border: `2px solid ${alpha(theme.palette.error.main, 0.3)}`,
                            '&:hover': {
                              bgcolor: alpha(theme.palette.error.main, 0.2),
                            }
                          }}
                        >
                          <Stop sx={{ color: theme.palette.error.main }} />
                        </IconButton>
                      </Tooltip>
                      
                      {/* Botões direcionais */}
                      <Box sx={{ position: 'absolute', top: 20 }}>
                        <Tooltip title="Para cima">
                          <IconButton 
                            onClick={() => handlePTZControl(0, 0.5, 0)}
                            disabled={!hasPTZ}
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.1),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.2) }
                            }}
                          >
                            <ArrowUpward />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      <Box sx={{ position: 'absolute', bottom: 20 }}>
                        <Tooltip title="Para baixo">
                          <IconButton 
                            onClick={() => handlePTZControl(0, -0.5, 0)}
                            disabled={!hasPTZ}
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.1),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.2) }
                            }}
                          >
                            <ArrowDownward />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      <Box sx={{ position: 'absolute', left: 20 }}>
                        <Tooltip title="Para esquerda">
                          <IconButton 
                            onClick={() => handlePTZControl(-0.5, 0, 0)}
                            disabled={!hasPTZ}
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.1),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.2) }
                            }}
                          >
                            <ArrowBack />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      <Box sx={{ position: 'absolute', right: 20 }}>
                        <Tooltip title="Para direita">
                          <IconButton 
                            onClick={() => handlePTZControl(0.5, 0, 0)}
                            disabled={!hasPTZ}
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.1),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.2) }
                            }}
                          >
                            <ArrowForward />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      {/* Botões diagonais */}
                      <Box sx={{ position: 'absolute', top: 50, left: 50 }}>
                        <Tooltip title="Diagonal superior esquerda">
                          <IconButton 
                            onClick={() => handlePTZControl(-0.35, 0.35, 0)}
                            disabled={!hasPTZ}
                            size="small"
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.05),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) }
                            }}
                          >
                            <ArrowUpward sx={{ transform: 'rotate(-45deg)' }} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      <Box sx={{ position: 'absolute', top: 50, right: 50 }}>
                        <Tooltip title="Diagonal superior direita">
                          <IconButton 
                            onClick={() => handlePTZControl(0.35, 0.35, 0)}
                            disabled={!hasPTZ}
                            size="small"
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.05),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) }
                            }}
                          >
                            <ArrowUpward sx={{ transform: 'rotate(45deg)' }} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      <Box sx={{ position: 'absolute', bottom: 50, left: 50 }}>
                        <Tooltip title="Diagonal inferior esquerda">
                          <IconButton 
                            onClick={() => handlePTZControl(-0.35, -0.35, 0)}
                            disabled={!hasPTZ}
                            size="small"
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.05),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) }
                            }}
                          >
                            <ArrowDownward sx={{ transform: 'rotate(45deg)' }} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      <Box sx={{ position: 'absolute', bottom: 50, right: 50 }}>
                        <Tooltip title="Diagonal inferior direita">
                          <IconButton 
                            onClick={() => handlePTZControl(0.35, -0.35, 0)}
                            disabled={!hasPTZ}
                            size="small"
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.05),
                              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) }
                            }}
                          >
                            <ArrowDownward sx={{ transform: 'rotate(-45deg)' }} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12} md={5}>
                <Card elevation={3} sx={{ 
                  borderRadius: 2, 
                  overflow: 'hidden',
                  height: '100%',
                  background: `linear-gradient(to bottom, ${alpha(theme.palette.background.paper, 0.8)}, ${theme.palette.background.paper})`,
                  backdropFilter: 'blur(10px)',
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
                }}>
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                      <ZoomIn sx={{ mr: 1, color: theme.palette.primary.main }} />
                      <Typography variant="h6" fontWeight="500">
                        Controle de Zoom
                      </Typography>
                    </Box>
                    
                    <Box sx={{ 
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 2,
                      mt: 2,
                      position: 'relative',
                      height: 200,
                      justifyContent: 'center'
                    }}>
                      {/* Linha vertical de zoom */}
                      <Box sx={{
                        position: 'absolute',
                        left: '50%',
                        top: '10%',
                        bottom: '10%',
                        width: '4px',
                        borderRadius: '4px',
                        background: `linear-gradient(to bottom, ${alpha(theme.palette.primary.main, 0.2)}, ${alpha(theme.palette.primary.main, 0.05)})`,
                      }} />
                      
                      <Tooltip title="Aumentar zoom">
                        <IconButton 
                          onClick={() => handlePTZControl(0, 0, 0.5)}
                          disabled={!hasPTZ}
                          sx={{ 
                            bgcolor: alpha(theme.palette.primary.main, 0.1),
                            '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.2) },
                            mb: 2
                          }}
                        >
                          <ZoomIn sx={{ fontSize: 30 }} />
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Diminuir zoom">
                        <IconButton 
                          onClick={() => handlePTZControl(0, 0, -0.5)}
                          disabled={!hasPTZ}
                          sx={{ 
                            bgcolor: alpha(theme.palette.primary.main, 0.1),
                            '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.2) },
                            mt: 2
                          }}
                        >
                          <ZoomOut sx={{ fontSize: 30 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                    
                    <Box sx={{ mt: 3, textAlign: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        Velocidade de movimento: Normal
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Tab de Presets */}
          <TabPanel value={tabValue} index={2}>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <BookmarkIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
                <Typography variant="h6" fontWeight="500">
                  Presets de Posição
                </Typography>
              </Box>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleOpenPresetDialog}
                disabled={!hasPTZ}
                sx={{ 
                  borderRadius: 2,
                  boxShadow: 2,
                  background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.primary.light})`,
                }}
              >
                Adicionar Preset
              </Button>
            </Box>
            
            {presets && presets.length > 0 ? (
              <Grid container spacing={2}>
                {presets.map((preset: CameraPreset) => (
                  <Grid item xs={12} sm={6} md={4} key={preset.id}>
                    <Card 
                      elevation={2} 
                      sx={{ 
                        borderRadius: 2,
                        overflow: 'hidden',
                        transition: 'transform 0.2s, box-shadow 0.2s',
                        '&:hover': {
                          transform: 'translateY(-4px)',
                          boxShadow: 4
                        },
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column'
                      }}
                    >
                      <Box sx={{ 
                        p: 2, 
                        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.dark, 0.8)}, ${alpha(theme.palette.primary.main, 0.6)})`,
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1
                      }}>
                        <LocationIcon fontSize="small" />
                        <Typography variant="subtitle1" fontWeight="500" noWrap>
                          {preset.name}
                        </Typography>
                      </Box>
                      
                      <CardContent sx={{ flexGrow: 1, pt: 2 }}>
                        {preset.description ? (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {preset.description}
                          </Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
                            Sem descrição
                          </Typography>
                        )}
                        
                        <Box sx={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: 1,
                          mt: 1
                        }}>
                          <Chip 
                            label={`Preset #${preset.id}`} 
                            size="small" 
                            sx={{ 
                              bgcolor: alpha(theme.palette.primary.main, 0.1),
                              color: theme.palette.primary.main,
                              fontWeight: 500
                            }} 
                          />
                        </Box>
                      </CardContent>
                      
                      <CardActions sx={{ 
                        p: 2, 
                        pt: 0,
                        borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                        justifyContent: 'space-between'
                      }}>
                        <Tooltip title="Ir para esta posição">
                          <Button
                            onClick={() => handleGotoPreset(preset.id)}
                            variant="contained"
                            size="small"
                            startIcon={<PlayArrowIcon />}
                            sx={{ 
                              borderRadius: 1.5,
                              boxShadow: 'none',
                              bgcolor: alpha(theme.palette.primary.main, 0.9),
                              '&:hover': {
                                bgcolor: theme.palette.primary.main,
                                boxShadow: 1
                              }
                            }}
                          >
                            Ir para
                          </Button>
                        </Tooltip>
                        
                        <Tooltip title="Excluir preset">
                          <IconButton
                            size="small"
                            onClick={() => handleDeletePreset(preset.id)}
                            sx={{ 
                              color: theme.palette.error.main,
                              bgcolor: alpha(theme.palette.error.main, 0.1),
                              '&:hover': {
                                bgcolor: alpha(theme.palette.error.main, 0.2)
                              }
                            }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Card 
                elevation={0} 
                sx={{ 
                  p: 4, 
                  textAlign: 'center',
                  borderRadius: 2,
                  border: `1px dashed ${alpha(theme.palette.primary.main, 0.3)}`,
                  bgcolor: alpha(theme.palette.primary.main, 0.03)
                }}
              >
                <BookmarkIcon sx={{ fontSize: 48, color: alpha(theme.palette.text.secondary, 0.5), mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Nenhum preset encontrado
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Crie presets para salvar posições específicas da câmera
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={handleOpenPresetDialog}
                  disabled={!hasPTZ}
                >
                  Adicionar Primeiro Preset
                </Button>
              </Card>
            )}
          </TabPanel>

          {/* Tab de Informações */}
          <TabPanel value={tabValue} index={3}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card elevation={2} sx={{ 
                  borderRadius: 2, 
                  overflow: 'hidden',
                  height: '100%',
                  background: `linear-gradient(to bottom, ${alpha(theme.palette.background.paper, 0.8)}, ${theme.palette.background.paper})`,
                  backdropFilter: 'blur(10px)',
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
                }}>
                  <Box sx={{ 
                    p: 2, 
                    background: `linear-gradient(135deg, ${alpha(theme.palette.primary.dark, 0.8)}, ${alpha(theme.palette.primary.main, 0.6)})`,
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}>
                    <VideocamIcon />
                    <Typography variant="h6" fontWeight="500">
                      Informações da Câmera
                    </Typography>
                  </Box>
                  
                  <CardContent sx={{ p: 0 }}>
                    <List sx={{ p: 0 }}>
                      <ListItem sx={{ 
                        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                        py: 1.5
                      }}>
                        <ListItemIcon>
                          <BadgeIcon sx={{ color: theme.palette.primary.main }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" color="text.secondary" fontWeight="500">
                              Nome
                            </Typography>
                          }
                          secondary={
                            <Typography variant="body1">
                              {camera?.name || 'N/A'}
                            </Typography>
                          }
                        />
                      </ListItem>
                      
                      <ListItem sx={{ 
                        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                        py: 1.5
                      }}>
                        <ListItemIcon>
                          <RouterIcon sx={{ color: theme.palette.primary.main }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" color="text.secondary" fontWeight="500">
                              Endereço IP
                            </Typography>
                          }
                          secondary={
                            <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'medium' }}>
                              {camera?.ip_address || 'N/A'}
                            </Typography>
                          }
                        />
                      </ListItem>
                      
                      <ListItem sx={{ 
                        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                        py: 1.5
                      }}>
                        <ListItemIcon>
                          <SettingsEthernetIcon sx={{ color: theme.palette.primary.main }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" color="text.secondary" fontWeight="500">
                              Porta
                            </Typography>
                          }
                          secondary={
                            <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'medium' }}>
                              {camera?.port || 'N/A'}
                            </Typography>
                          }
                        />
                      </ListItem>
                      
                      <ListItem sx={{ 
                        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                        py: 1.5
                      }}>
                        <ListItemIcon>
                          <PersonIcon sx={{ color: theme.palette.primary.main }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" color="text.secondary" fontWeight="500">
                              Usuário
                            </Typography>
                          }
                          secondary={
                            <Typography variant="body1">
                              {camera?.username || 'N/A'}
                            </Typography>
                          }
                        />
                      </ListItem>
                      
                      <ListItem sx={{ 
                        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                        py: 1.5
                      }}>
                        <ListItemIcon>
                          <LocationOnIcon sx={{ color: theme.palette.primary.main }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" color="text.secondary" fontWeight="500">
                              Localização
                            </Typography>
                          }
                          secondary={
                            <Typography variant="body1">
                              {camera?.location || 'N/A'}
                            </Typography>
                          }
                        />
                      </ListItem>
                      
                      <ListItem sx={{ 
                        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                        py: 1.5
                      }}>
                        <ListItemIcon>
                          <BusinessIcon sx={{ color: theme.palette.primary.main }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" color="text.secondary" fontWeight="500">
                              Fabricante
                            </Typography>
                          }
                          secondary={
                            <Typography variant="body1">
                              {camera?.manufacturer || 'N/A'}
                            </Typography>
                          }
                        />
                      </ListItem>
                      
                      <ListItem sx={{ py: 1.5 }}>
                        <ListItemIcon>
                          <DevicesIcon sx={{ color: theme.palette.primary.main }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" color="text.secondary" fontWeight="500">
                              Modelo
                            </Typography>
                          }
                          secondary={
                            <Typography variant="body1">
                              {camera?.model || 'N/A'}
                            </Typography>
                          }
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Card elevation={2} sx={{ 
                  borderRadius: 2, 
                  overflow: 'hidden',
                  height: '100%',
                  background: `linear-gradient(to bottom, ${alpha(theme.palette.background.paper, 0.8)}, ${theme.palette.background.paper})`,
                  backdropFilter: 'blur(10px)',
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
                }}>
                  <Box sx={{ 
                    p: 2, 
                    background: `linear-gradient(135deg, ${alpha(theme.palette.secondary.dark, 0.8)}, ${alpha(theme.palette.secondary.main, 0.6)})`,
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}>
                    <MemoryIcon />
                    <Typography variant="h6" fontWeight="500">
                      Informações do Dispositivo
                    </Typography>
                  </Box>
                  
                  <CardContent sx={{ p: 0 }}>
                    {deviceInfo ? (
                      <List sx={{ p: 0 }}>
                        <ListItem sx={{ 
                          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                          py: 1.5
                        }}>
                          <ListItemIcon>
                            <BusinessIcon sx={{ color: theme.palette.secondary.main }} />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Typography variant="body2" color="text.secondary" fontWeight="500">
                                Fabricante
                              </Typography>
                            }
                            secondary={
                              <Typography variant="body1">
                                {deviceInfo.manufacturer || 'N/A'}
                              </Typography>
                            }
                          />
                        </ListItem>
                        
                        <ListItem sx={{ 
                          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                          py: 1.5
                        }}>
                          <ListItemIcon>
                            <DevicesIcon sx={{ color: theme.palette.secondary.main }} />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Typography variant="body2" color="text.secondary" fontWeight="500">
                                Modelo
                              </Typography>
                            }
                            secondary={
                              <Typography variant="body1">
                                {deviceInfo.model || 'N/A'}
                              </Typography>
                            }
                          />
                        </ListItem>
                        
                        <ListItem sx={{ 
                          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                          py: 1.5
                        }}>
                          <ListItemIcon>
                            <SystemUpdateAltIcon sx={{ color: theme.palette.secondary.main }} />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Typography variant="body2" color="text.secondary" fontWeight="500">
                                Firmware
                              </Typography>
                            }
                            secondary={
                              <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'medium' }}>
                                {deviceInfo.firmware_version || 'N/A'}
                              </Typography>
                            }
                          />
                        </ListItem>
                        
                        <ListItem sx={{ 
                          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                          py: 1.5
                        }}>
                          <ListItemIcon>
                            <VpnKeyIcon sx={{ color: theme.palette.secondary.main }} />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Typography variant="body2" color="text.secondary" fontWeight="500">
                                Número de Série
                              </Typography>
                            }
                            secondary={
                              <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'medium' }}>
                                {deviceInfo.serial_number || 'N/A'}
                              </Typography>
                            }
                          />
                        </ListItem>
                        
                        <ListItem sx={{ py: 1.5 }}>
                          <ListItemIcon>
                            <SettingsEthernetIcon sx={{ color: theme.palette.secondary.main }} />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Typography variant="body2" color="text.secondary" fontWeight="500">
                                ID de Hardware
                              </Typography>
                            }
                            secondary={
                              <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'medium' }}>
                                {deviceInfo.hardware_id || 'N/A'}
                              </Typography>
                            }
                          />
                        </ListItem>
                      </List>
                    ) : (
                      <Box sx={{ p: 4, textAlign: 'center' }}>
                        <CircularProgress size={40} sx={{ mb: 2 }} />
                        <Typography>Carregando informações do dispositivo...</Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Card elevation={2} sx={{ 
                  borderRadius: 2, 
                  overflow: 'hidden',
                  background: `linear-gradient(to bottom, ${alpha(theme.palette.background.paper, 0.8)}, ${theme.palette.background.paper})`,
                  backdropFilter: 'blur(10px)',
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`
                }}>
                  <Box sx={{ 
                    p: 2, 
                    background: `linear-gradient(135deg, ${alpha(theme.palette.info.dark, 0.8)}, ${alpha(theme.palette.info.main, 0.6)})`,
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}>
                    <SettingsIcon />
                    <Typography variant="h6" fontWeight="500">
                      Capacidades da Câmera
                    </Typography>
                  </Box>
                  
                  <CardContent>
                    {capabilities ? (
                      <Box sx={{ mt: 1 }}>
                        <Grid container spacing={2}>
                          {/* PTZ Capability */}
                          <Grid item xs={6} sm={4} md={4} lg={2}>
                            <Card elevation={1} sx={{
                              height: '100%',
                              borderRadius: 2,
                              background: capabilities.ptz 
                                ? `linear-gradient(135deg, ${alpha(theme.palette.success.light, 0.2)}, ${alpha(theme.palette.success.main, 0.05)})` 
                                : `linear-gradient(135deg, ${alpha(theme.palette.text.disabled, 0.1)}, ${alpha(theme.palette.background.paper, 0.8)})`,
                              border: capabilities.ptz 
                                ? `1px solid ${alpha(theme.palette.success.main, 0.3)}` 
                                : `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                              transition: 'transform 0.2s, box-shadow 0.2s',
                              '&:hover': {
                                transform: 'translateY(-2px)',
                                boxShadow: 2
                              }
                            }}>
                              <CardContent sx={{ p: 2, textAlign: 'center' }}>
                                <Box sx={{
                                  width: 48,
                                  height: 48,
                                  borderRadius: '50%',
                                  display: 'flex',
                                  justifyContent: 'center',
                                  alignItems: 'center',
                                  margin: '0 auto 16px',
                                  background: capabilities.ptz 
                                    ? `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.light})` 
                                    : alpha(theme.palette.text.disabled, 0.2),
                                  boxShadow: capabilities.ptz ? 2 : 0
                                }}>
                                  <PanToolIcon sx={{ 
                                    color: capabilities.ptz ? 'white' : alpha(theme.palette.text.primary, 0.4),
                                    fontSize: 24
                                  }} />
                                </Box>
                                <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                                  PTZ
                                </Typography>
                                <Chip 
                                  label={capabilities.ptz ? "Disponível" : "Indisponível"}
                                  size="small"
                                  color={capabilities.ptz ? "success" : "default"}
                                  sx={{ 
                                    fontWeight: 'medium',
                                    ...(capabilities.ptz && {
                                      '& .MuiChip-label': { color: theme.palette.success.dark }
                                    })
                                  }}
                                />
                              </CardContent>
                            </Card>
                          </Grid>

                          {/* Events Capability */}
                          <Grid item xs={6} sm={4} md={4} lg={2}>
                            <Card elevation={1} sx={{
                              height: '100%',
                              borderRadius: 2,
                              background: capabilities.events 
                                ? `linear-gradient(135deg, ${alpha(theme.palette.success.light, 0.2)}, ${alpha(theme.palette.success.main, 0.05)})` 
                                : `linear-gradient(135deg, ${alpha(theme.palette.text.disabled, 0.1)}, ${alpha(theme.palette.background.paper, 0.8)})`,
                              border: capabilities.events 
                                ? `1px solid ${alpha(theme.palette.success.main, 0.3)}` 
                                : `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                              transition: 'transform 0.2s, box-shadow 0.2s',
                              '&:hover': {
                                transform: 'translateY(-2px)',
                                boxShadow: 2
                              }
                            }}>
                              <CardContent sx={{ p: 2, textAlign: 'center' }}>
                                <Box sx={{
                                  width: 48,
                                  height: 48,
                                  borderRadius: '50%',
                                  display: 'flex',
                                  justifyContent: 'center',
                                  alignItems: 'center',
                                  margin: '0 auto 16px',
                                  background: capabilities.events 
                                    ? `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.light})` 
                                    : alpha(theme.palette.text.disabled, 0.2),
                                  boxShadow: capabilities.events ? 2 : 0
                                }}>
                                  <NotificationsIcon sx={{ 
                                    color: capabilities.events ? 'white' : alpha(theme.palette.text.primary, 0.4),
                                    fontSize: 24
                                  }} />
                                </Box>
                                <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                                  Eventos
                                </Typography>
                                <Chip 
                                  label={capabilities.events ? "Disponível" : "Indisponível"}
                                  size="small"
                                  color={capabilities.events ? "success" : "default"}
                                  sx={{ 
                                    fontWeight: 'medium',
                                    ...(capabilities.events && {
                                      '& .MuiChip-label': { color: theme.palette.success.dark }
                                    })
                                  }}
                                />
                              </CardContent>
                            </Card>
                          </Grid>

                          {/* Imaging Capability */}
                          <Grid item xs={6} sm={4} md={4} lg={2}>
                            <Card elevation={1} sx={{
                              height: '100%',
                              borderRadius: 2,
                              background: capabilities.imaging 
                                ? `linear-gradient(135deg, ${alpha(theme.palette.success.light, 0.2)}, ${alpha(theme.palette.success.main, 0.05)})` 
                                : `linear-gradient(135deg, ${alpha(theme.palette.text.disabled, 0.1)}, ${alpha(theme.palette.background.paper, 0.8)})`,
                              border: capabilities.imaging 
                                ? `1px solid ${alpha(theme.palette.success.main, 0.3)}` 
                                : `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                              transition: 'transform 0.2s, box-shadow 0.2s',
                              '&:hover': {
                                transform: 'translateY(-2px)',
                                boxShadow: 2
                              }
                            }}>
                              <CardContent sx={{ p: 2, textAlign: 'center' }}>
                                <Box sx={{
                                  width: 48,
                                  height: 48,
                                  borderRadius: '50%',
                                  display: 'flex',
                                  justifyContent: 'center',
                                  alignItems: 'center',
                                  margin: '0 auto 16px',
                                  background: capabilities.imaging 
                                    ? `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.light})` 
                                    : alpha(theme.palette.text.disabled, 0.2),
                                  boxShadow: capabilities.imaging ? 2 : 0
                                }}>
                                  <ImageIcon sx={{ 
                                    color: capabilities.imaging ? 'white' : alpha(theme.palette.text.primary, 0.4),
                                    fontSize: 24
                                  }} />
                                </Box>
                                <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                                  Imagem
                                </Typography>
                                <Chip 
                                  label={capabilities.imaging ? "Disponível" : "Indisponível"}
                                  size="small"
                                  color={capabilities.imaging ? "success" : "default"}
                                  sx={{ 
                                    fontWeight: 'medium',
                                    ...(capabilities.imaging && {
                                      '& .MuiChip-label': { color: theme.palette.success.dark }
                                    })
                                  }}
                                />
                              </CardContent>
                            </Card>
                          </Grid>

                          {/* Media Capability */}
                          <Grid item xs={6} sm={4} md={4} lg={2}>
                            <Card elevation={1} sx={{
                              height: '100%',
                              borderRadius: 2,
                              background: capabilities.media 
                                ? `linear-gradient(135deg, ${alpha(theme.palette.success.light, 0.2)}, ${alpha(theme.palette.success.main, 0.05)})` 
                                : `linear-gradient(135deg, ${alpha(theme.palette.text.disabled, 0.1)}, ${alpha(theme.palette.background.paper, 0.8)})`,
                              border: capabilities.media 
                                ? `1px solid ${alpha(theme.palette.success.main, 0.3)}` 
                                : `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                              transition: 'transform 0.2s, box-shadow 0.2s',
                              '&:hover': {
                                transform: 'translateY(-2px)',
                                boxShadow: 2
                              }
                            }}>
                              <CardContent sx={{ p: 2, textAlign: 'center' }}>
                                <Box sx={{
                                  width: 48,
                                  height: 48,
                                  borderRadius: '50%',
                                  display: 'flex',
                                  justifyContent: 'center',
                                  alignItems: 'center',
                                  margin: '0 auto 16px',
                                  background: capabilities.media 
                                    ? `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.light})` 
                                    : alpha(theme.palette.text.disabled, 0.2),
                                  boxShadow: capabilities.media ? 2 : 0
                                }}>
                                  <VideoLibraryIcon sx={{ 
                                    color: capabilities.media ? 'white' : alpha(theme.palette.text.primary, 0.4),
                                    fontSize: 24
                                  }} />
                                </Box>
                                <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                                  Mídia
                                </Typography>
                                <Chip 
                                  label={capabilities.media ? "Disponível" : "Indisponível"}
                                  size="small"
                                  color={capabilities.media ? "success" : "default"}
                                  sx={{ 
                                    fontWeight: 'medium',
                                    ...(capabilities.media && {
                                      '& .MuiChip-label': { color: theme.palette.success.dark }
                                    })
                                  }}
                                />
                              </CardContent>
                            </Card>
                          </Grid>

                          {/* Analytics Capability */}
                          <Grid item xs={6} sm={4} md={4} lg={2}>
                            <Card elevation={1} sx={{
                              height: '100%',
                              borderRadius: 2,
                              background: capabilities.analytics 
                                ? `linear-gradient(135deg, ${alpha(theme.palette.success.light, 0.2)}, ${alpha(theme.palette.success.main, 0.05)})` 
                                : `linear-gradient(135deg, ${alpha(theme.palette.text.disabled, 0.1)}, ${alpha(theme.palette.background.paper, 0.8)})`,
                              border: capabilities.analytics 
                                ? `1px solid ${alpha(theme.palette.success.main, 0.3)}` 
                                : `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                              transition: 'transform 0.2s, box-shadow 0.2s',
                              '&:hover': {
                                transform: 'translateY(-2px)',
                                boxShadow: 2
                              }
                            }}>
                              <CardContent sx={{ p: 2, textAlign: 'center' }}>
                                <Box sx={{
                                  width: 48,
                                  height: 48,
                                  borderRadius: '50%',
                                  display: 'flex',
                                  justifyContent: 'center',
                                  alignItems: 'center',
                                  margin: '0 auto 16px',
                                  background: capabilities.analytics 
                                    ? `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.light})` 
                                    : alpha(theme.palette.text.disabled, 0.2),
                                  boxShadow: capabilities.analytics ? 2 : 0
                                }}>
                                  <AssessmentIcon sx={{ 
                                    color: capabilities.analytics ? 'white' : alpha(theme.palette.text.primary, 0.4),
                                    fontSize: 24
                                  }} />
                                </Box>
                                <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                                  Analytics
                                </Typography>
                                <Chip 
                                  label={capabilities.analytics ? "Disponível" : "Indisponível"}
                                  size="small"
                                  color={capabilities.analytics ? "success" : "default"}
                                  sx={{ 
                                    fontWeight: 'medium',
                                    ...(capabilities.analytics && {
                                      '& .MuiChip-label': { color: theme.palette.success.dark }
                                    })
                                  }}
                                />
                              </CardContent>
                            </Card>
                          </Grid>

                          {/* Audio Capability */}
                          <Grid item xs={12} sm={6} md={4} key="audio">
                            <Box sx={{
                              p: 2,
                              height: '100%',
                              borderRadius: 2,
                              background: false 
                                ? `linear-gradient(135deg, ${alpha(theme.palette.success.light, 0.2)}, ${alpha(theme.palette.success.main, 0.05)})` 
                                : `linear-gradient(135deg, ${alpha(theme.palette.text.disabled, 0.1)}, ${alpha(theme.palette.background.paper, 0.8)})`,
                              border: false 
                                ? `1px solid ${alpha(theme.palette.success.main, 0.3)}` 
                                : `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                              transition: 'transform 0.2s, box-shadow 0.2s',
                              '&:hover': {
                                transform: 'translateY(-4px)',
                                boxShadow: 4
                              }
                            }}>
                              <Box sx={{ 
                                display: 'flex', 
                                flexDirection: 'column',
                                height: '100%'
                              }}>
                                <Box sx={{
                                  width: 56,
                                  height: 56,
                                  borderRadius: '50%',
                                  display: 'flex',
                                  justifyContent: 'center',
                                  alignItems: 'center',
                                  margin: '0 auto 16px',
                                  background: false 
                                    ? `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.light})` 
                                    : alpha(theme.palette.text.disabled, 0.2),
                                  boxShadow: false ? 2 : 0
                                }}>
                                  <MicIcon sx={{ 
                                    color: false ? 'white' : alpha(theme.palette.text.primary, 0.4),
                                    fontSize: 24
                                  }} />
                                </Box>
                                
                                <Typography variant="subtitle1" align="center" gutterBottom fontWeight="medium">
                                  Áudio
                                </Typography>
                                <Chip 
                                  label={"Indisponível"}
                                  size="small"
                                  color={"default"}
                                  sx={{ 
                                    fontWeight: 'medium'
                                  }}
                                  variant="outlined"
                                />
                              </Box>
                            </Box>
                          </Grid>
                        </Grid>
                      </Box>
                    ) : capabilitiesLoading ? (
                      <Box sx={{ p: 4, textAlign: 'center' }}>
                        <CircularProgress size={40} sx={{ mb: 2 }} />
                        <Typography>Carregando capacidades da câmera...</Typography>
                      </Box>
                    ) : (
                      <Box sx={{ p: 4, textAlign: 'center' }}>
                        <WarningIcon sx={{ fontSize: 48, color: alpha(theme.palette.warning.main, 0.7), mb: 2 }} />
                        <Typography variant="h6" color="text.secondary" gutterBottom>
                          Capacidades não disponíveis
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Não foi possível obter as capacidades desta câmera.
                        </Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Tab de Simulação */}
          <TabPanel value={tabValue} index={4}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card elevation={3} sx={{ borderRadius: 2, overflow: 'hidden', height: '100%' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                      <SimulationIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
                      <Typography variant="h6" fontWeight="500">
                        Simulação de Câmera
                      </Typography>
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" paragraph>
                      Faça upload de uma imagem para simular o screenshot da câmera ou insira uma URL de vídeo para processamento com detecção de objetos em tempo real.
                    </Typography>
                    
                    <Box sx={{
                      border: `2px dashed ${alpha(theme.palette.primary.main, 0.3)}`,
                      borderRadius: 2,
                      p: 3,
                      textAlign: 'center',
                      backgroundColor: alpha(theme.palette.primary.main, 0.03),
                      mb: 3
                    }}>
                      <input
                        accept="image/*"
                        style={{ display: 'none' }}
                        id="screenshot-upload"
                        type="file"
                        onChange={handleImageUpload}
                      />
                      <label htmlFor="screenshot-upload">
                        <Button
                          variant="outlined"
                          component="span"
                          startIcon={<CameraAltIcon />}
                          sx={{
                            mb: 2,
                            borderRadius: 1.5,
                            borderColor: alpha(theme.palette.primary.main, 0.5),
                            '&:hover': {
                              borderColor: theme.palette.primary.main,
                              backgroundColor: alpha(theme.palette.primary.main, 0.05)
                            }
                          }}
                        >
                          Selecionar Imagem
                        </Button>
                      </label>
                      
                      <Typography variant="body2" color="text.secondary">
                        Formatos suportados: JPG, PNG, GIF (máx. 5MB)
                      </Typography>
                    </Box>
                    
                    {uploadStatus === 'loading' && (
                      <Box sx={{ textAlign: 'center', my: 2 }}>
                        <CircularProgress size={30} />
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          Processando imagem...
                        </Typography>
                      </Box>
                    )}
                    
                    {uploadStatus === 'error' && (
                      <Box sx={{
                        p: 2,
                        bgcolor: alpha(theme.palette.error.main, 0.1),
                        borderRadius: 1,
                        display: 'flex',
                        alignItems: 'center',
                        mb: 3
                      }}>
                        <WarningIcon color="error" sx={{ mr: 1 }} />
                        <Typography color="error.main">{uploadMessage}</Typography>
                      </Box>
                    )}
                    
                    {uploadStatus === 'success' && (
                      <Box sx={{
                        p: 2,
                        bgcolor: alpha(theme.palette.success.main, 0.1),
                        borderRadius: 1,
                        display: 'flex',
                        alignItems: 'center',
                        mb: 3
                      }}>
                        <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                        <Typography color="success.main">{uploadMessage}</Typography>
                      </Box>
                    )}
                    
                    <Button
                      variant="contained"
                      fullWidth
                      disabled={!imageBase64 || uploadStatus === 'loading'}
                      onClick={(e) => {
                        e.preventDefault();
                        console.log('Botão Salvar Screenshot clicado!');
                        if (imageBase64 && cameraId) {
                          console.log(`Salvando screenshot para câmera ID: ${cameraId}`);
                          handleSaveScreenshot();
                        } else {
                          console.error('Faltando dados para salvar screenshot:', { 
                            temImagem: !!imageBase64, 
                            cameraId 
                          });
                        }
                      }}
                      startIcon={<SaveIcon />}
                      sx={{
                        mt: 2,
                        borderRadius: 1.5,
                        background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
                        boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.3)}`,
                        '&:hover': {
                          boxShadow: `0 6px 16px ${alpha(theme.palette.primary.main, 0.4)}`,
                        },
                        '&.Mui-disabled': {
                          background: alpha(theme.palette.action.disabled, 0.2)
                        }
                      }}
                    >
                      Salvar Screenshot
                    </Button>
                    
                    <Divider sx={{ my: 4 }} />
                    
                    <Box sx={{ mb: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <VideocamIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
                        <Typography variant="h6" fontWeight="500">
                          Processamento de Vídeo com YOLO
                        </Typography>
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" paragraph>
                        Insira a URL de um vídeo para processar com detecção de objetos em tempo real usando YOLO.
                      </Typography>
                      
                      <TextField
                        fullWidth
                        label="URL do Vídeo"
                        variant="outlined"
                        placeholder="https://exemplo.com/video.mp4"
                        margin="normal"
                        value={videoUrl}
                        onChange={(e) => setVideoUrl(e.target.value)}
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <VideocamIcon color="primary" />
                            </InputAdornment>
                          ),
                        }}
                        helperText="Formatos suportados: MP4, WebM, OGG"
                      />
                      
                      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                        <Button
                          variant="contained"
                          color="primary"
                          onClick={handleProcessVideo}
                          startIcon={<PlayArrowIcon />}
                          disabled={!videoUrl || processingVideo}
                          sx={{ 
                            minWidth: '180px',
                            borderRadius: 1.5,
                            background: `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.dark})`,
                            boxShadow: `0 4px 12px ${alpha(theme.palette.success.main, 0.3)}`,
                            '&:hover': {
                              boxShadow: `0 6px 16px ${alpha(theme.palette.success.main, 0.4)}`,
                            },
                          }}
                        >
                          {processingVideo ? 'Processando...' : 'Processar Vídeo'}
                        </Button>
                        {processingVideo && (
                          <Button
                            variant="outlined"
                            color="error"
                            onClick={handleStopProcessing}
                            startIcon={<StopIcon />}
                            sx={{ ml: 2 }}
                          >
                            Parar
                          </Button>
                        )}
                      </Box>
                      
                      {videoProcessingError && (
                        <Box sx={{
                          p: 2,
                          mt: 2,
                          bgcolor: alpha(theme.palette.error.main, 0.1),
                          borderRadius: 1,
                          display: 'flex',
                          alignItems: 'center'
                        }}>
                          <WarningIcon color="error" sx={{ mr: 1 }} />
                          <Typography color="error.main">{videoProcessingError}</Typography>
                        </Box>
                      )}
                    </Box>
                    
                    {processingVideo && (
                      <Box sx={{ mt: 3, textAlign: 'center' }}>
                        <Typography variant="subtitle1" gutterBottom fontWeight="500">
                          Detecção em tempo real
                        </Typography>
                        <Box
                          sx={{
                            position: 'relative',
                            width: '100%',
                            height: '400px',
                            backgroundColor: '#000',
                            borderRadius: 2,
                            overflow: 'hidden',
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            boxShadow: 3
                          }}
                        >
                          {processedFrame ? (
                            <img 
                              src={processedFrame} 
                              alt="Processed Video" 
                              style={{ maxWidth: '100%', maxHeight: '100%' }} 
                            />
                          ) : (
                            <CircularProgress />
                          )}
                        </Box>
                        
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="subtitle2" gutterBottom fontWeight="500">
                            Objetos Detectados:
                          </Typography>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 1 }}>
                            {detectedObjects.map((obj, index) => (
                              <Chip 
                                key={index}
                                label={`${obj.class_name} (${Math.round(obj.confidence * 100)}%)`}
                                color="primary"
                                variant="outlined"
                                size="small"
                              />
                            ))}
                            {detectedObjects.length === 0 && (
                              <Typography variant="body2" color="text.secondary">
                                Nenhum objeto detectado ainda...
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Card elevation={3} sx={{ borderRadius: 2, overflow: 'hidden', height: '100%' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                      <ImageIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
                      <Typography variant="h6" fontWeight="500">
                        Pré-visualização
                      </Typography>
                    </Box>
                    
                    {previewImage ? (
                      <Box sx={{
                        width: '100%',
                        height: 300,
                        borderRadius: 2,
                        overflow: 'hidden',
                        position: 'relative',
                        boxShadow: 2
                      }}>
                        <img
                          src={previewImage}
                          alt="Preview"
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                          }}
                        />
                      </Box>
                    ) : (
                      <Box sx={{
                        width: '100%',
                        height: 300,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        borderRadius: 2,
                        bgcolor: alpha(theme.palette.text.disabled, 0.1),
                        border: `1px dashed ${alpha(theme.palette.text.disabled, 0.3)}`
                      }}>
                        <ImageIcon sx={{ fontSize: 48, color: alpha(theme.palette.text.secondary, 0.5), mb: 2 }} />
                        <Typography variant="body1" color="text.secondary">
                          Nenhuma imagem selecionada
                        </Typography>
                        <Typography variant="body2" color="text.disabled" sx={{ mt: 1 }}>
                          A pré-visualização aparecerá aqui
                        </Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>
        </>
      )}

      {/* Diálogo para criar preset */}
      <Dialog 
        open={openPresetDialog} 
        onClose={handleClosePresetDialog}
        PaperProps={{
          sx: {
            borderRadius: 2,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
            background: `linear-gradient(to bottom, ${alpha(theme.palette.background.paper, 0.95)}, ${theme.palette.background.paper})`,
            backdropFilter: 'blur(10px)',
            border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
            overflow: 'hidden'
          }
        }}
        maxWidth="sm"
        fullWidth
      >
        <Box sx={{ 
          p: 2, 
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.dark, 0.8)}, ${alpha(theme.palette.primary.main, 0.6)})`,
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          gap: 1
        }}>
          <BookmarkIcon />
          <DialogTitle sx={{ p: 0, color: 'white', fontWeight: 500 }}>
            Criar Novo Preset
          </DialogTitle>
        </Box>
        
        <DialogContent sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Salve a posição atual da câmera como um preset para acesso rápido no futuro.
          </Typography>
          
          <TextField
            autoFocus
            margin="dense"
            id="preset-name"
            label="Nome do Preset"
            type="text"
            fullWidth
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            variant="outlined"
            sx={{
              mb: 2,
              '& .MuiOutlinedInput-root': {
                borderRadius: 1.5,
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: theme.palette.primary.main,
                  borderWidth: 2
                }
              }
            }}
            InputProps={{
              startAdornment: (
                <Box sx={{ color: alpha(theme.palette.primary.main, 0.7), mr: 1 }}>
                  <LocationOnIcon fontSize="small" />
                </Box>
              )
            }}
          />
          
          <TextField
            margin="dense"
            id="preset-description"
            label="Descrição (opcional)"
            type="text"
            fullWidth
            multiline
            rows={3}
            value={presetDescription}
            onChange={(e) => setPresetDescription(e.target.value)}
            variant="outlined"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 1.5,
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: theme.palette.primary.main,
                  borderWidth: 2
                }
              }
            }}
            InputProps={{
              startAdornment: (
                <Box sx={{ color: alpha(theme.palette.primary.main, 0.7), mr: 1, mt: 1 }}>
                  <InfoIcon fontSize="small" />
                </Box>
              )
            }}
          />
        </DialogContent>
        
        <DialogActions sx={{ px: 3, py: 2, borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}` }}>
          <Button 
            onClick={handleClosePresetDialog}
            variant="outlined"
            startIcon={<CancelIcon />}
            sx={{ 
              borderRadius: 1.5,
              borderColor: alpha(theme.palette.text.secondary, 0.3),
              color: theme.palette.text.secondary,
              '&:hover': {
                borderColor: alpha(theme.palette.text.secondary, 0.6),
                backgroundColor: alpha(theme.palette.text.secondary, 0.05)
              }
            }}
          >
            Cancelar
          </Button>
          
          <Button
            onClick={handleCreatePreset}
            variant="contained"
            disabled={!presetName || createPresetMutation.isPending}
            startIcon={createPresetMutation.isPending ? null : <SaveIcon />}
            sx={{ 
              borderRadius: 1.5,
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
              boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.3)}`,
              px: 3,
              '&:hover': {
                boxShadow: `0 6px 16px ${alpha(theme.palette.primary.main, 0.4)}`,
              },
              '&.Mui-disabled': {
                background: alpha(theme.palette.action.disabled, 0.2)
              }
            }}
          >
            {createPresetMutation.isPending ? <CircularProgress size={24} /> : 'Salvar Preset'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CameraDetail;
