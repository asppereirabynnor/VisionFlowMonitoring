import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  FormHelperText,
  Alert,
  AlertTitle,
  Chip,
  Stack,
  OutlinedInput,
  SelectChangeEvent,
  LinearProgress,
  Modal,
  IconButton,
  Grid
} from '@mui/material';
import { styled } from '@mui/material/styles';
import VideoFileIcon from '@mui/icons-material/VideoFile';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CloseIcon from '@mui/icons-material/Close';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import DeleteIcon from '@mui/icons-material/Delete';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../config';

// Classes disponíveis para detecção
const AVAILABLE_CLASSES = [
  'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
  'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
  'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
  'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
  'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
  'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
  'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
  'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
  'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
  'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
];

// Estilos
const VideoContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginTop: theme.spacing(2),
  marginBottom: theme.spacing(2),
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
}));

const VideoPlayer = styled('video')({
  maxWidth: '100%',
  maxHeight: '500px',
  backgroundColor: '#000',
  objectFit: 'contain',
});

const VideoModal = styled(Modal)({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
});

const ModalContent = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.background.paper,
  boxShadow: theme.shadows[24],
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  maxWidth: '90vw',
  maxHeight: '90vh',
  display: 'flex',
  flexDirection: 'column',
  position: 'relative',
}));

const ModalHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: theme.spacing(2),
}));

const ModalVideoContainer = styled(Box)({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  overflow: 'hidden',
  backgroundColor: '#000',
  flex: 1,
});

// Interface para status de processamento
interface ProcessingStatus {
  video_id: string;
  status: 'queued' | 'downloading' | 'processing' | 'completed' | 'failed';
  progress?: number;
  error?: string;
  total_frames?: number;
  processed_frames?: number;
}

const VideoProcessor: React.FC = () => {
  const { token } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [processedVideoUrl, setProcessedVideoUrl] = useState<string | null>(null);
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.5);
  const [statusCheckInterval, setStatusCheckInterval] = useState<NodeJS.Timeout | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Limpar intervalo quando o componente for desmontado
  useEffect(() => {
    return () => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, [statusCheckInterval]);

  // Verificar status periodicamente quando houver um ID de processamento
  useEffect(() => {
    if (processingId && !statusCheckInterval) {
      const interval = setInterval(() => {
        checkProcessingStatus(processingId);
      }, 3000); // Verificar a cada 3 segundos
      setStatusCheckInterval(interval);
    } else if (!processingId && statusCheckInterval) {
      clearInterval(statusCheckInterval);
      setStatusCheckInterval(null);
    }
  }, [processingId, statusCheckInterval]);

  // Função para selecionar arquivo
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const file = event.target.files[0];
      // Verificar se é um arquivo de vídeo
      if (file.type.startsWith('video/')) {
        setSelectedFile(file);
        setError(null);
      } else {
        setError('Por favor, selecione um arquivo de vídeo válido (MP4, WebM, OGG)');
        setSelectedFile(null);
      }
    }
  };

  // Função para limpar o arquivo selecionado
  const clearSelectedFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Função para iniciar o processamento do vídeo
  const processVideo = async (): Promise<void> => {
    if (!selectedFile) {
      setError('Por favor, selecione um arquivo de vídeo');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setProcessingId(null);
      setProcessedVideoUrl(null);
      setStatus(null);
      setUploadProgress(0);

      // Criar um FormData para enviar o arquivo
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      // Adicionar parâmetros adicionais
      if (selectedClasses.length > 0) {
        selectedClasses.forEach(className => {
          formData.append('detect_classes', className);
        });
      }
      formData.append('confidence_threshold', confidenceThreshold.toString());

      // Usar XMLHttpRequest para monitorar o progresso do upload
      const xhr = new XMLHttpRequest();
      
      // Configurar a promessa para o upload
      const uploadPromise = new Promise<any>((resolve, reject) => {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const percentComplete = Math.round((event.loaded / event.total) * 100);
            setUploadProgress(percentComplete);
          }
        });
        
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              resolve(response);
            } catch (e) {
              reject(new Error('Erro ao processar resposta do servidor'));
            }
          } else {
            try {
              const errorData = JSON.parse(xhr.responseText);
              reject(new Error(errorData.detail || `Erro ${xhr.status}: ${xhr.statusText}`));
            } catch (e) {
              reject(new Error(`Erro ${xhr.status}: ${xhr.statusText}`));
            }
          }
        });
        
        xhr.addEventListener('error', () => {
          reject(new Error('Erro de conexão ao enviar o arquivo'));
        });
        
        xhr.addEventListener('abort', () => {
          reject(new Error('Upload cancelado'));
        });
      });
      
      // Configurar e enviar a requisição
      xhr.open('POST', `${API_URL}/video-download/upload-video`);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);
      
      // Aguardar a conclusão do upload
      const data = await uploadPromise;
      setProcessingId(data.processed_video_id);
      
      // Iniciar verificação de status
      checkProcessingStatus(data.processed_video_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido ao processar vídeo');
    } finally {
      setLoading(false);
    }
  };

  // Verificar o status do processamento
  const checkProcessingStatus = async (videoId: string): Promise<void> => {
    try {
      const response = await fetch(`${API_URL}/video-download/video-status/${videoId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Erro ao verificar status do processamento');
      }

      const statusData = await response.json();
      
      // Log para depuração do progresso
      console.log('Status de processamento recebido:', {
        status: statusData.status,
        progress: statusData.progress,
        processed_frames: statusData.processed_frames,
        total_frames: statusData.total_frames
      });
      
      setStatus(statusData);

      // Se o processamento foi concluído, parar de verificar o status
      if (statusData.status === 'completed' || statusData.status === 'failed') {
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval);
          setStatusCheckInterval(null);
        }
      }
    } catch (err) {
      console.error('Erro ao verificar status:', err);
    }
  };

  // Baixar o vídeo processado
  const downloadProcessedVideo = async (): Promise<void> => {
    if (processingId && token) {
      try {
        setLoading(true);
        console.log('Iniciando download do vídeo com ID:', processingId);
        
        // Usar o novo endpoint que aceita token como parâmetro de consulta
        const downloadUrl = `${API_URL}/video-download/public-download/${processingId}?token=${token}`;
        
        // Criar elemento de link para download direto
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = downloadUrl;
        a.download = `processed_video_${processingId}.mp4`;
        
        // Adicionar à página, clicar e remover
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        setLoading(false);
        console.log('Download iniciado com sucesso');
      } catch (err) {
        console.error('Erro ao iniciar download:', err);
        setError(err instanceof Error ? err.message : 'Erro ao baixar vídeo');
        setLoading(false);
      }
    } else {
      console.error('Faltando processingId ou token:', { processingId, tokenExiste: !!token });
      setError('Faltando ID de processamento ou token de autenticação');
    }
  };

  // Carregar o vídeo processado para visualização
  const loadProcessedVideo = async (): Promise<void> => {
    if (processingId && token) {
      try {
        setLoading(true);
        setError(null); // Limpar erros anteriores
        console.log('Carregando vídeo para visualização...');
        
        // Usar o novo endpoint que aceita token como parâmetro de consulta
        // Adicionar timestamp para evitar problemas de cache
        const timestamp = new Date().getTime();
        const videoUrl = `${API_URL}/video-download/public-download/${processingId}?token=${token}&t=${timestamp}`;
        
        // Assumimos que o vídeo está pronto se o status atual é 'completed'
        if (status?.status !== 'completed') {
          throw new Error('O vídeo ainda não está pronto para visualização.');
        }
        
        // Usar a página HTML intermediária para reprodução do vídeo
        const encodedVideoUrl = encodeURIComponent(videoUrl);
        const playerUrl = `/video-player.html?url=${encodedVideoUrl}`;
        
        // Abrir o player em uma nova janela
        window.open(playerUrl, '_blank');
        
        console.log('Player de vídeo aberto em nova janela');
        setLoading(false);
      } catch (err) {
        console.error('Erro ao preparar URL do vídeo:', err);
        setError(err instanceof Error ? err.message : 'Erro ao preparar URL do vídeo');
        setLoading(false);
      }
    }
  };
  
  // Alternar modo tela cheia para o vídeo
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };
  
  // Fechar o modal de vídeo
  const handleCloseModal = () => {
    setModalOpen(false);
  };

  // Manipular mudança nas classes selecionadas
  const handleClassChange = (event: SelectChangeEvent<typeof selectedClasses>) => {
    const { target: { value } } = event;
    setSelectedClasses(
      typeof value === 'string' ? value.split(',') : value,
    );
  };

  // Manipular mudança no threshold de confiança
  const handleConfidenceChange = (_event: Event, newValue: number | number[]) => {
    setConfidenceThreshold(newValue as number);
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1000, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        <VideoFileIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Processamento de Vídeo com YOLO
      </Typography>
      
      <Typography variant="body1" paragraph>
        Selecione um arquivo de vídeo local para processar com detecção de objetos
        usando YOLO. Formatos suportados: MP4, WebM, OGG.
      </Typography>
      
      <Box component="form" noValidate sx={{ mt: 2 }}>
        <input
          type="file"
          accept="video/*"
          style={{ display: 'none' }}
          id="video-upload-input"
          onChange={handleFileSelect}
          ref={fileInputRef}
        />
        <label htmlFor="video-upload-input">
          <Button
            variant="outlined"
            component="span"
            startIcon={<CloudUploadIcon />}
            sx={{ mb: 2, mr: 2 }}
          >
            Selecionar Vídeo
          </Button>
        </label>
        
        {selectedFile && (
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <VideoFileIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="body2" sx={{ flexGrow: 1, mr: 2 }}>
              {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
            </Typography>
            <IconButton onClick={clearSelectedFile} size="small">
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Box>
        )}

        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel id="classes-select-label">Classes para Detectar</InputLabel>
              <Select
                labelId="classes-select-label"
                multiple
                value={selectedClasses}
                onChange={handleClassChange}
                input={<OutlinedInput label="Classes para Detectar" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} />
                    ))}
                  </Box>
                )}
              >
                {AVAILABLE_CLASSES.map((className) => (
                  <MenuItem key={className} value={className}>
                    {className}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Box sx={{ mb: 2 }}>
              <Typography id="confidence-slider" gutterBottom>
                Threshold de Confiança: {confidenceThreshold}
              </Typography>
              <Slider
                value={confidenceThreshold}
                onChange={handleConfidenceChange}
                aria-labelledby="confidence-slider"
                step={0.05}
                marks
                min={0.1}
                max={0.9}
                valueLabelDisplay="auto"
              />
            </Box>
          </Grid>
        </Grid>

        <Button
          variant="contained"
          color="primary"
          onClick={processVideo}
          disabled={loading || !selectedFile}
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
          sx={{ mb: 2 }}
        >
          {loading ? 'Enviando...' : 'Processar Vídeo'}
        </Button>
        
        {loading && uploadProgress > 0 && (
          <Box sx={{ width: '100%', mb: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Enviando arquivo: {uploadProgress}%
            </Typography>
            <LinearProgress variant="determinate" value={uploadProgress} />
          </Box>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {status && (
        <Paper sx={{ p: 2, mt: 2 }}>
          <Typography variant="h6">Status do Processamento</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            <Typography variant="body1" sx={{ mr: 1 }}>
              Status:
            </Typography>
            <Chip
              label={status.status.toUpperCase()}
              color={
                status.status === 'completed' ? 'success' :
                status.status === 'failed' ? 'error' :
                'primary'
              }
              variant="outlined"
            />
          </Box>
          
          {/* Exibir barra de progresso durante o processamento */}
          {(status.status === 'processing' || status.status === 'downloading') && status.progress !== undefined && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  {status.status === 'processing' ? 'Processando vídeo:' : 'Baixando vídeo:'} {Math.round(status.progress)}%
                </Typography>
                {status.processed_frames !== undefined && status.total_frames !== undefined && (
                  <Typography variant="body2" color="text.secondary">
                    {status.processed_frames} / {status.total_frames} frames
                  </Typography>
                )}
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={status.progress} 
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          )}
          
          {status.status === 'failed' && status.error && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {status.error}
            </Alert>
          )}

          {status.status === 'completed' && (
            <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                color="primary"
                startIcon={<CloudDownloadIcon />}
                onClick={downloadProcessedVideo}
              >
                Download Vídeo
              </Button>
              <Button
                variant="outlined"
                color="primary"
                startIcon={<PlayArrowIcon />}
                onClick={loadProcessedVideo}
              >
                Visualizar
              </Button>
            </Box>
          )}
        </Paper>
      )}

      {/* Modal para visualização do vídeo */}
      <VideoModal
        open={modalOpen}
        onClose={handleCloseModal}
        aria-labelledby="video-modal-title"
        aria-describedby="video-modal-description"
      >
        <ModalContent sx={{ width: isFullscreen ? '95vw' : '80vw', height: isFullscreen ? '95vh' : 'auto' }}>
          <ModalHeader>
            <Typography variant="h6" component="h2" id="video-modal-title">
              Vídeo Processado
            </Typography>
            <Box>
              <IconButton onClick={toggleFullscreen} size="small" sx={{ mr: 1 }}>
                <FullscreenIcon />
              </IconButton>
              <IconButton onClick={handleCloseModal} size="small">
                <CloseIcon />
              </IconButton>
            </Box>
          </ModalHeader>
          
          <ModalVideoContainer sx={{ height: isFullscreen ? 'calc(95vh - 80px)' : '500px' }}>
            {processedVideoUrl && (
              <>
                <Box sx={{ 
                  width: '100%', 
                  height: isFullscreen ? 'calc(95vh - 80px)' : '500px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <iframe
                    src={processedVideoUrl}
                    title="Vídeo Processado"
                    width="100%"
                    height="100%"
                    style={{ border: 'none', maxHeight: isFullscreen ? 'calc(95vh - 80px)' : '500px' }}
                    allowFullScreen
                  />
                </Box>
                {error && (
                  <Alert severity="error" sx={{ mt: 2, width: '100%' }}>
                    {error}
                  </Alert>
                )}
              </>
            )}
          </ModalVideoContainer>
          
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2, gap: 2 }}>
            <Button
              variant="contained"
              color="primary"
              onClick={downloadProcessedVideo}
              startIcon={<CloudDownloadIcon />}
            >
              Download Vídeo
            </Button>
          </Box>
        </ModalContent>
      </VideoModal>
    </Box>
  );
};

export default VideoProcessor;
