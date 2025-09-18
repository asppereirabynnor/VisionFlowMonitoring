import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  CardMedia,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Grid,
  IconButton,
  TextField,
  Typography,
  CircularProgress,
  Switch,
  FormControlLabel,
  Paper,
  Chip,
  Divider,
  Tooltip,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Videocam as VideocamIcon,
  Visibility as VisibilityIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Settings as SettingsIcon,
  LocationOn as LocationIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCameras, createCamera, updateCamera, deleteCamera, Camera } from '../services/cameraService';

const CameraList: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [openDialog, setOpenDialog] = useState(false);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    rtsp_url: '',
    ip_address: '',
    port: 554,
    username: '',
    password: '',
    onvif_url: '',
    description: '',
    location: '',
    is_active: true,
  });

  // Buscar câmeras
  const { data: cameras, isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: getCameras,
  });

  // Mutação para criar câmera
  const createMutation = useMutation(
    createCamera,
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['cameras'] });
        handleCloseDialog();
      },
    }
  );

  // Mutação para atualizar câmera
  const updateMutation = useMutation(
    ({ id, data }: { id: number; data: Partial<Camera> }) => updateCamera(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['cameras'] });
        handleCloseDialog();
      },
    }
  );

  // Mutação para excluir câmera
  const deleteMutation = useMutation(
    deleteCamera,
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['cameras'] });
        handleCloseDeleteDialog();
      },
    }
  );

  const handleOpenDialog = (camera?: Camera) => {
    if (camera) {
      setSelectedCamera(camera);
      setFormData({
        name: camera.name,
        rtsp_url: camera.rtsp_url,
        ip_address: camera.ip_address,
        port: camera.port,
        username: camera.username,
        password: camera.password,
        onvif_url: camera.onvif_url || '',
        description: camera.description || '',
        location: camera.location || '',
        is_active: camera.is_active,
      });
    } else {
      setSelectedCamera(null);
      setFormData({
        name: '',
        rtsp_url: '',
        ip_address: '',
        port: 554,
        username: '',
        password: '',
        onvif_url: '',
        description: '',
        location: '',
        is_active: true,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleOpenDeleteDialog = (camera: Camera) => {
    setSelectedCamera(camera);
    setOpenDeleteDialog(true);
  };

  const handleCloseDeleteDialog = () => {
    setOpenDeleteDialog(false);
    setSelectedCamera(null);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked } = e.target;
    setFormData({
      ...formData,
      [name]: name === 'is_active' ? checked : value,
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedCamera) {
      updateMutation.mutate({ id: selectedCamera.id, data: formData });
    } else {
      createMutation.mutate(formData as any);
    }
  };

  const handleDelete = () => {
    if (selectedCamera) {
      deleteMutation.mutate(selectedCamera.id);
    }
  };

  const handleViewCamera = (id: number) => {
    navigate(`/cameras/${id}`);
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Paper 
        elevation={0} 
        sx={{ 
          p: 3, 
          mb: 4, 
          borderRadius: 2,
          background: (theme) => `linear-gradient(135deg, ${theme.palette.primary.dark}, ${theme.palette.primary.main})`,
          color: 'white',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <Box 
          sx={{ 
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            opacity: 0.1,
            background: 'url("data:image/svg+xml,%3Csvg width=\'100\' height=\'100\' viewBox=\'0 0 100 100\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cpath d=\'M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z\' fill=\'%23ffffff\' fill-opacity=\'1\' fill-rule=\'evenodd\'/%3E%3C/svg%3E")',
          }}
        />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'relative', zIndex: 1 }}>
          <Box>
            <Typography variant="h4" fontWeight="bold" sx={{ mb: 1 }}>
              Sistema de Monitoramento Inteligente
            </Typography>
            <Typography variant="subtitle1" sx={{ opacity: 0.9, fontWeight: 300 }}>
              Gerencie suas câmeras de segurança e configure o monitoramento inteligente
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
            sx={{ 
              bgcolor: 'white', 
              color: 'primary.main',
              fontWeight: 'bold',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.9)' },
              borderRadius: 2,
              boxShadow: '0 4px 10px rgba(0,0,0,0.15)',
              px: 3
            }}
          >
            Adicionar Câmera
          </Button>
        </Box>
      </Paper>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Typography variant="h5" fontWeight="500">
          Câmeras Disponíveis
        </Typography>
        <Chip 
          label={`${cameras?.length || 0} câmeras`} 
          color="primary" 
          variant="outlined" 
          size="small"
        />
      </Box>

      <Grid container spacing={3}>
        {cameras && cameras.length > 0 ? 
          cameras.map((camera) => {
              const statusColor = camera.is_active 
                ? theme.palette.success.main 
                : theme.palette.error.main;
              
              return (
              <Grid item xs={12} sm={6} md={4} key={camera.id}>
              <Card 
                elevation={3} 
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform 0.3s, box-shadow 0.3s',
                  '&:hover': {
                    transform: 'translateY(-5px)',
                    boxShadow: '0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23)',
                  },
                  borderTop: `3px solid ${statusColor}`,
                  position: 'relative',
                  overflow: 'visible'
                }}
              >
                <Box
                  sx={{
                    position: 'absolute',
                    top: -15,
                    right: 20,
                    width: 30,
                    height: 30,
                    borderRadius: '50%',
                    backgroundColor: statusColor,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 3px 5px rgba(0,0,0,0.2)',
                    zIndex: 10, // Aumentar o z-index para garantir que fique acima da imagem
                  }}
                >
                  {camera.is_active ? 
                    <CheckCircleIcon sx={{ color: 'white', fontSize: 20 }} /> : 
                    <CancelIcon sx={{ color: 'white', fontSize: 20 }} />}
                </Box>
                
                <CardMedia
                  component="div"
                  sx={{
                    height: 160,
                    background: camera.screenshot_base64 
                      ? 'none' 
                      : `linear-gradient(135deg, ${alpha(theme.palette.primary.dark, 0.8)}, ${alpha(theme.palette.primary.main, 0.4)})`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    overflow: 'hidden',
                    marginTop: '10px', // Adicionar margem superior para dar espaço ao ícone de status
                    zIndex: 1, // Definir z-index menor que o ícone de status
                  }}
                >
                  {camera.screenshot_base64 ? (
                    <img 
                      src={camera.screenshot_base64} 
                      alt={camera.name}
                      style={{ 
                        width: '100%', 
                        height: '100%', 
                        objectFit: 'cover',
                      }} 
                    />
                  ) : (
                    <>
                      <Box
                        sx={{
                          position: 'absolute',
                          width: '100%',
                          height: '100%',
                          background: 'repeating-linear-gradient(45deg, rgba(255,255,255,0.05), rgba(255,255,255,0.05) 10px, rgba(0,0,0,0.05) 10px, rgba(0,0,0,0.05) 20px)',
                        }}
                      />
                      <VideocamIcon sx={{ fontSize: 70, color: 'white', opacity: 0.8, filter: 'drop-shadow(0 2px 5px rgba(0,0,0,0.3))' }} />
                    </>
                  )}
                </CardMedia>
                
                <CardContent sx={{ flexGrow: 1, pt: 3 }}>
                  <Typography gutterBottom variant="h5" component="div" fontWeight="500">
                    {camera.name}
                  </Typography>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Chip 
                      label={camera.is_active ? 'Online' : 'Offline'}
                      size="small"
                      sx={{ 
                        backgroundColor: camera.is_active ? alpha(theme.palette.success.main, 0.1) : alpha(theme.palette.error.main, 0.1),
                        color: camera.is_active ? theme.palette.success.dark : theme.palette.error.dark,
                        fontWeight: 500,
                        mr: 1
                      }}
                    />
                    {camera.location && (
                      <Tooltip title={`Localização: ${camera.location}`}>
                        <Chip 
                          icon={<LocationIcon sx={{ fontSize: '0.8rem !important' }} />} 
                          label={camera.location} 
                          size="small"
                          sx={{ 
                            backgroundColor: alpha(theme.palette.info.main, 0.1),
                            color: theme.palette.info.dark,
                          }}
                        />
                      </Tooltip>
                    )}
                  </Box>
                  
                  <Divider sx={{ my: 1.5 }} />
                  
                  <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                    <Box component="span" sx={{ fontWeight: 500, mr: 1, color: 'text.primary' }}>RTSP:</Box>
                    <Box component="span" sx={{ 
                      maxWidth: '100%', 
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {camera.rtsp_url}
                    </Box>
                  </Typography>
                  
                  {camera.onvif_url && (
                    <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box component="span" sx={{ fontWeight: 500, mr: 1, color: 'text.primary' }}>ONVIF:</Box>
                      <Box component="span" sx={{ 
                        maxWidth: '100%', 
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        {camera.onvif_url}
                      </Box>
                    </Typography>
                  )}
                  
                  {camera.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                      {camera.description}
                    </Typography>
                  )}
                </CardContent>
                
                <Divider />
                
                <CardActions sx={{ justifyContent: 'space-between', px: 2, py: 1.5 }}>
                  <Button 
                    size="small" 
                    onClick={() => handleViewCamera(camera.id)}
                    startIcon={<VisibilityIcon />}
                    variant="contained"
                    color="primary"
                    sx={{ borderRadius: 4 }}
                  >
                    Visualizar
                  </Button>
                  
                  <Box>
                    <Tooltip title="Editar">
                      <IconButton 
                        onClick={() => handleOpenDialog(camera)}
                        size="small"
                        sx={{ 
                          backgroundColor: alpha(theme.palette.warning.main, 0.1),
                          mr: 1,
                          '&:hover': { backgroundColor: alpha(theme.palette.warning.main, 0.2) }
                        }}
                      >
                        <EditIcon fontSize="small" color="warning" />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Excluir">
                      <IconButton 
                        onClick={() => handleOpenDeleteDialog(camera)}
                        size="small"
                        sx={{ 
                          backgroundColor: alpha(theme.palette.error.main, 0.1),
                          '&:hover': { backgroundColor: alpha(theme.palette.error.main, 0.2) }
                        }}
                      >
                        <DeleteIcon fontSize="small" color="error" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </CardActions>
              </Card>
            </Grid>
          );
          })
        : (
          <Grid item xs={12}>
            <Paper 
              elevation={2} 
              sx={{ 
                p: 4, 
                textAlign: 'center',
                borderRadius: 2,
                backgroundColor: (theme) => alpha(theme.palette.info.main, 0.05)
              }}
            >
              <VideocamIcon sx={{ fontSize: 60, color: 'text.secondary', opacity: 0.5, mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Nenhuma câmera encontrada
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Clique no botão "Adicionar Câmera" para começar
              </Typography>
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* Diálogo para adicionar/editar câmera */}
      <Dialog 
        open={openDialog} 
        onClose={handleCloseDialog} 
        maxWidth="md"
        PaperProps={{
          sx: {
            borderRadius: 2,
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }
        }}
      >
        <DialogTitle sx={{ 
          borderBottom: '1px solid',
          borderColor: 'divider',
          py: 2,
          px: 3,
          bgcolor: (theme) => alpha(theme.palette.primary.main, 0.05),
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <VideocamIcon sx={{ mr: 1.5, color: 'primary.main' }} />
            <Typography variant="h6" component="span" fontWeight="500">
              {selectedCamera ? 'Editar Câmera' : 'Adicionar Nova Câmera'}
            </Typography>
          </Box>
        </DialogTitle>
        
        <DialogContent sx={{ p: 3 }}>
          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight="500" color="primary" sx={{ mb: 1 }}>
                  Informações Básicas
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  fullWidth
                  id="name"
                  label="Nome da Câmera"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  id="location"
                  label="Localização"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  id="description"
                  label="Descrição"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  variant="outlined"
                  multiline
                  rows={2}
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sx={{ mt: 2 }}>
                <Typography variant="subtitle2" fontWeight="500" color="primary" sx={{ mb: 1 }}>
                  Configuração de Conexão
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>
              
              <Grid item xs={12} sm={8}>
                <TextField
                  required
                  fullWidth
                  id="ip_address"
                  label="Endereço IP"
                  name="ip_address"
                  value={formData.ip_address}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={4}>
                <TextField
                  required
                  fullWidth
                  id="port"
                  label="Porta"
                  name="port"
                  type="number"
                  value={formData.port}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  required
                  fullWidth
                  id="rtsp_url"
                  label="URL RTSP"
                  name="rtsp_url"
                  value={formData.rtsp_url}
                  onChange={handleChange}
                  variant="outlined"
                  placeholder="rtsp://ip:porta/stream"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  id="onvif_url"
                  label="URL ONVIF"
                  name="onvif_url"
                  value={formData.onvif_url}
                  onChange={handleChange}
                  variant="outlined"
                  placeholder="http://ip:porta/onvif/device_service"
                  helperText="Ex: http://192.168.1.100:8080/onvif/device_service"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sx={{ mt: 2 }}>
                <Typography variant="subtitle2" fontWeight="500" color="primary" sx={{ mb: 1 }}>
                  Credenciais de Acesso
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  id="username"
                  label="Usuário"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  id="password"
                  label="Senha"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{
                    sx: { borderRadius: 1.5 }
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sx={{ mt: 2 }}>
                <Paper 
                  variant="outlined" 
                  sx={{ 
                    p: 2, 
                    borderRadius: 2,
                    bgcolor: (theme) => alpha(theme.palette.success.main, 0.05),
                    borderColor: (theme) => alpha(theme.palette.success.main, 0.2),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography variant="body2" fontWeight="500" sx={{ mr: 1 }}>
                      Status da Câmera
                    </Typography>
                    <Chip 
                      label={formData.is_active ? "Ativa" : "Inativa"}
                      size="small"
                      color={formData.is_active ? "success" : "default"}
                      variant="outlined"
                    />
                  </Box>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.is_active}
                        onChange={handleChange}
                        name="is_active"
                        color="success"
                      />
                    }
                    label={formData.is_active ? "Ativar" : "Desativar"}
                    sx={{ m: 0 }}
                  />
                </Paper>
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        
        <DialogActions sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
          <Button 
            onClick={handleCloseDialog}
            variant="outlined"
            sx={{ borderRadius: 2 }}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={createMutation.isPending || updateMutation.isPending}
            startIcon={createMutation.isPending || updateMutation.isPending ? <CircularProgress size={20} /> : null}
            sx={{ borderRadius: 2, px: 3 }}
          >
            {createMutation.isPending || updateMutation.isPending ? 'Salvando...' : 'Salvar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Diálogo para confirmar exclusão */}
      <Dialog 
        open={openDeleteDialog} 
        onClose={handleCloseDeleteDialog}
        PaperProps={{
          sx: {
            borderRadius: 2,
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            maxWidth: '450px',
            width: '100%'
          }
        }}
      >
        <DialogTitle sx={{ 
          borderBottom: '1px solid',
          borderColor: 'divider',
          py: 2,
          px: 3,
          bgcolor: (theme) => alpha(theme.palette.error.main, 0.05),
          color: 'error.main',
          display: 'flex',
          alignItems: 'center',
        }}>
          <DeleteIcon sx={{ mr: 1.5 }} />
          <Typography variant="h6" component="span" fontWeight="500">
            Confirmar Exclusão
          </Typography>
        </DialogTitle>
        
        <DialogContent sx={{ p: 3, pt: 3 }}>
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            textAlign: 'center',
            mb: 2
          }}>
            <Box 
              sx={{ 
                width: 60, 
                height: 60, 
                borderRadius: '50%', 
                bgcolor: (theme) => alpha(theme.palette.error.main, 0.1),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: 2
              }}
            >
              <DeleteIcon color="error" sx={{ fontSize: 30 }} />
            </Box>
            
            <Typography variant="h6" gutterBottom>
              Excluir Câmera
            </Typography>
          </Box>
          
          <DialogContentText sx={{ textAlign: 'center' }}>
            Tem certeza que deseja excluir a câmera <Box component="span" sx={{ fontWeight: 'bold' }}>"{selectedCamera?.name}"</Box>?
            <Box component="p" sx={{ mt: 1, color: 'text.secondary' }}>
              Esta ação não pode ser desfeita e todos os dados associados serão removidos permanentemente.
            </Box>
          </DialogContentText>
        </DialogContent>
        
        <DialogActions sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider', justifyContent: 'center' }}>
          <Button 
            onClick={handleCloseDeleteDialog}
            variant="outlined"
            sx={{ borderRadius: 2, minWidth: 100 }}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleDelete}
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
            startIcon={deleteMutation.isPending ? <CircularProgress size={20} color="inherit" /> : null}
            sx={{ borderRadius: 2, minWidth: 100 }}
          >
            {deleteMutation.isPending ? 'Excluindo...' : 'Excluir'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CameraList;
