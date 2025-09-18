import React, { useState, useEffect } from 'react';
import { 
  Grid, 
  Paper, 
  Typography, 
  Box, 
  Card, 
  CardContent, 
  CardHeader,
  CircularProgress,
  Divider,
  IconButton,
  Tooltip,
  alpha,
  useTheme,
  Chip,
  LinearProgress,
  Avatar
} from '@mui/material';
import {
  Videocam as VideocamIcon,
  VideocamOff as VideocamOffIcon,
  Notifications as NotificationsIcon,
  NotificationsActive as NotificationsActiveIcon,
  MoreVert as MoreVertIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Warning as WarningIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { getCameras } from '../services/cameraService';
import { getEvents, getEventStats } from '../services/eventService';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({
    totalCameras: 0,
    activeCameras: 0,
    totalEvents: 0,
    todayEvents: 0
  });

  // Buscar câmeras
  const { data: cameras, isLoading: camerasLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: getCameras
  });

  // Buscar eventos recentes
  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['events'],
    queryFn: () => getEvents({ limit: 10 })
  });

  // Buscar estatísticas de eventos
  const { data: eventStats, isLoading: statsLoading } = useQuery({
    queryKey: ['eventStats'],
    queryFn: () => getEventStats()
  });

  useEffect(() => {
    if (cameras && events && eventStats) {
      // Calcular estatísticas
      const today = new Date().toISOString().split('T')[0];
      const todayEvents = events.filter(event => 
        event.timestamp && typeof event.timestamp === 'string' && event.timestamp.startsWith(today)
      ).length;

      setStats({
        totalCameras: cameras.length,
        activeCameras: cameras.filter(camera => camera.is_active).length,
        totalEvents: events.length,
        todayEvents
      });
    }
  }, [cameras, events, eventStats]);

  const isLoading = camerasLoading || eventsLoading || statsLoading;

  const theme = useTheme();

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
              Dashboard de Monitoramento
            </Typography>
            <Typography variant="subtitle1" sx={{ opacity: 0.9, fontWeight: 300 }}>
              Visão geral do sistema de monitoramento inteligente
            </Typography>
          </Box>
          <Tooltip title="Atualizar dados">
            <IconButton sx={{ color: 'white', bgcolor: 'rgba(255,255,255,0.1)', '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' } }}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Paper>
      
      {/* Cards de estatísticas */}
      <Typography variant="h5" fontWeight="500" sx={{ mb: 2 }}>
        Estatísticas do Sistema
      </Typography>
      
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 3, 
              borderRadius: 2,
              height: '100%',
              position: 'relative',
              overflow: 'hidden',
              transition: 'transform 0.2s',
              '&:hover': { transform: 'translateY(-5px)' },
              borderLeft: `4px solid ${theme.palette.primary.main}`
            }}
          >
            <Box sx={{ 
              position: 'absolute', 
              top: 0, 
              right: 0, 
              p: 1.5,
              color: alpha(theme.palette.primary.main, 0.2),
              transform: 'scale(2.5)',
              transformOrigin: 'top right'
            }}>
              <VideocamIcon fontSize="large" />
            </Box>
            
            <Typography variant="subtitle2" color="text.secondary" fontWeight="500">
              TOTAL DE CÂMERAS
            </Typography>
            <Typography variant="h3" sx={{ my: 1, fontWeight: 600 }}>
              {stats.totalCameras}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Chip 
                size="small" 
                label={`${stats.activeCameras} ativas`} 
                sx={{ 
                  bgcolor: alpha(theme.palette.success.main, 0.1),
                  color: theme.palette.success.dark,
                  fontWeight: 500
                }} 
              />
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 3, 
              borderRadius: 2,
              height: '100%',
              position: 'relative',
              overflow: 'hidden',
              transition: 'transform 0.2s',
              '&:hover': { transform: 'translateY(-5px)' },
              borderLeft: `4px solid ${theme.palette.success.main}`
            }}
          >
            <Box sx={{ 
              position: 'absolute', 
              top: 0, 
              right: 0, 
              p: 1.5,
              color: alpha(theme.palette.success.main, 0.2),
              transform: 'scale(2.5)',
              transformOrigin: 'top right'
            }}>
              <CheckCircleIcon fontSize="large" />
            </Box>
            
            <Typography variant="subtitle2" color="text.secondary" fontWeight="500">
              CÂMERAS ATIVAS
            </Typography>
            <Typography variant="h3" sx={{ my: 1, fontWeight: 600 }}>
              {stats.activeCameras}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <LinearProgress 
                variant="determinate" 
                value={stats.totalCameras > 0 ? (stats.activeCameras / stats.totalCameras) * 100 : 0} 
                sx={{ 
                  width: '100%', 
                  height: 6, 
                  borderRadius: 3,
                  bgcolor: alpha(theme.palette.success.main, 0.1),
                  '& .MuiLinearProgress-bar': {
                    bgcolor: theme.palette.success.main
                  }
                }} 
              />
              <Typography variant="caption" sx={{ ml: 1, fontWeight: 500 }}>
                {stats.totalCameras > 0 ? Math.round((stats.activeCameras / stats.totalCameras) * 100) : 0}%
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 3, 
              borderRadius: 2,
              height: '100%',
              position: 'relative',
              overflow: 'hidden',
              transition: 'transform 0.2s',
              '&:hover': { transform: 'translateY(-5px)' },
              borderLeft: `4px solid ${theme.palette.info.main}`
            }}
          >
            <Box sx={{ 
              position: 'absolute', 
              top: 0, 
              right: 0, 
              p: 1.5,
              color: alpha(theme.palette.info.main, 0.2),
              transform: 'scale(2.5)',
              transformOrigin: 'top right'
            }}>
              <NotificationsIcon fontSize="large" />
            </Box>
            
            <Typography variant="subtitle2" color="text.secondary" fontWeight="500">
              TOTAL DE EVENTOS
            </Typography>
            <Typography variant="h3" sx={{ my: 1, fontWeight: 600 }}>
              {stats.totalEvents}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <InfoIcon sx={{ fontSize: 16, color: theme.palette.info.main, mr: 0.5 }} />
              <Typography variant="caption" sx={{ fontWeight: 500 }}>
                Eventos detectados pelo sistema
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 3, 
              borderRadius: 2,
              height: '100%',
              position: 'relative',
              overflow: 'hidden',
              transition: 'transform 0.2s',
              '&:hover': { transform: 'translateY(-5px)' },
              borderLeft: `4px solid ${theme.palette.warning.main}`
            }}
          >
            <Box sx={{ 
              position: 'absolute', 
              top: 0, 
              right: 0, 
              p: 1.5,
              color: alpha(theme.palette.warning.main, 0.2),
              transform: 'scale(2.5)',
              transformOrigin: 'top right'
            }}>
              <NotificationsActiveIcon fontSize="large" />
            </Box>
            
            <Typography variant="subtitle2" color="text.secondary" fontWeight="500">
              EVENTOS HOJE
            </Typography>
            <Typography variant="h3" sx={{ my: 1, fontWeight: 600 }}>
              {stats.todayEvents}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Chip 
                size="small" 
                label="Hoje" 
                sx={{ 
                  bgcolor: alpha(theme.palette.warning.main, 0.1),
                  color: theme.palette.warning.dark,
                  fontWeight: 500
                }} 
              />
            </Box>
          </Paper>
        </Grid>
      </Grid>
      
      <Grid container spacing={3}>
        {/* Eventos recentes */}
        <Grid item xs={12} md={6}>
          <Card elevation={2} sx={{ borderRadius: 2, height: '100%' }}>
            <CardHeader 
              title={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <NotificationsIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6" fontWeight="500">Eventos Recentes</Typography>
                </Box>
              }
              action={
                <Tooltip title="Mais opções">
                  <IconButton>
                    <MoreVertIcon />
                  </IconButton>
                </Tooltip>
              }
              sx={{ 
                pb: 0,
                '& .MuiCardHeader-action': { m: 0 } 
              }}
            />
            <CardContent sx={{ pt: 0 }}>
              <Divider sx={{ mt: 1, mb: 2 }} />
              
              {events && events.length > 0 ? (
                events.slice(0, 5).map((event) => {
                  // Verificar se timestamp é válido antes de criar a data
                  let eventDate = new Date();
                  try {
                    if (event.timestamp && typeof event.timestamp === 'string') {
                      eventDate = new Date(event.timestamp);
                      // Verificar se a data é válida
                      if (isNaN(eventDate.getTime())) {
                        eventDate = new Date(); // Usar data atual como fallback
                      }
                    }
                  } catch (e) {
                    console.error('Erro ao processar data do evento:', e);
                    eventDate = new Date(); // Usar data atual como fallback
                  }
                  
                  // Garantir que confidence seja um número entre 0 e 1
                  let confidenceValue = 0;
                  if (event.confidence !== undefined) {
                    // Se confidence for maior que 1, assumimos que já está em porcentagem
                    confidenceValue = event.confidence > 1 ? event.confidence / 100 : event.confidence;
                    // Garantir que esteja entre 0 e 1
                    confidenceValue = Math.min(Math.max(confidenceValue, 0), 1);
                  }
                  
                  const confidenceLevel = confidenceValue * 100;
                  let confidenceColor = theme.palette.success.main;
                  
                  if (confidenceLevel < 50) {
                    confidenceColor = theme.palette.error.main;
                  } else if (confidenceLevel < 75) {
                    confidenceColor = theme.palette.warning.main;
                  }
                  
                  return (
                    <Paper 
                      key={event.id} 
                      variant="outlined" 
                      sx={{ 
                        mb: 2, 
                        p: 2, 
                        borderRadius: 2,
                        borderLeft: `3px solid ${confidenceColor}`,
                        transition: 'transform 0.2s',
                        '&:hover': { transform: 'translateX(5px)' },
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <Typography variant="subtitle1" fontWeight="500">
                          {event.event_type}
                        </Typography>
                        <Chip 
                          label={`${confidenceLevel.toFixed(1)}%`}
                          size="small"
                          sx={{ 
                            bgcolor: alpha(confidenceColor, 0.1),
                            color: confidenceColor,
                            fontWeight: 'bold',
                            minWidth: 60
                          }}
                        />
                      </Box>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                        <Avatar 
                          sx={{ 
                            width: 24, 
                            height: 24, 
                            mr: 1, 
                            bgcolor: alpha(theme.palette.primary.main, 0.1),
                            color: theme.palette.primary.main,
                            fontSize: '0.8rem',
                            fontWeight: 'bold'
                          }}
                        >
                          {event.camera_name ? event.camera_name.charAt(0).toUpperCase() : 'C'}
                        </Avatar>
                        <Typography variant="body2" color="text.secondary">
                          {event.camera_name || `Câmera ${event.camera_id}`}
                        </Typography>
                      </Box>
                      
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                        {!isNaN(eventDate.getTime()) ? 
                          `${eventDate.toLocaleDateString()} às ${eventDate.toLocaleTimeString()}` : 
                          'Data não disponível'}
                      </Typography>
                    </Paper>
                  );
                })
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <InfoIcon sx={{ fontSize: 40, color: 'text.secondary', opacity: 0.5, mb: 1 }} />
                  <Typography>Nenhum evento recente encontrado.</Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        {/* Lista de câmeras */}
        <Grid item xs={12} md={6}>
          <Card elevation={2} sx={{ borderRadius: 2, height: '100%' }}>
            <CardHeader 
              title={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <VideocamIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6" fontWeight="500">Câmeras</Typography>
                </Box>
              }
              action={
                <Tooltip title="Mais opções">
                  <IconButton>
                    <MoreVertIcon />
                  </IconButton>
                </Tooltip>
              }
              sx={{ 
                pb: 0,
                '& .MuiCardHeader-action': { m: 0 } 
              }}
            />
            <CardContent sx={{ pt: 0 }}>
              <Divider sx={{ mt: 1, mb: 2 }} />
              
              {cameras && cameras.length > 0 ? (
                cameras.map((camera) => (
                  <Paper 
                    key={camera.id} 
                    variant="outlined" 
                    sx={{ 
                      mb: 2, 
                      p: 2, 
                      borderRadius: 2,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'transform 0.2s',
                      '&:hover': { transform: 'translateX(5px)' },
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Avatar 
                        sx={{ 
                          bgcolor: camera.is_active 
                            ? alpha(theme.palette.success.main, 0.1) 
                            : alpha(theme.palette.error.main, 0.1),
                          color: camera.is_active 
                            ? theme.palette.success.main 
                            : theme.palette.error.main,
                          mr: 2
                        }}
                      >
                        {camera.is_active 
                          ? <VideocamIcon fontSize="small" /> 
                          : <VideocamOffIcon fontSize="small" />}
                      </Avatar>
                      
                      <Box>
                        <Typography variant="subtitle1" fontWeight="500">
                          {camera.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          {camera.rtsp_url}
                        </Typography>
                      </Box>
                    </Box>
                    
                    <Chip 
                      label={camera.is_active ? 'Online' : 'Offline'}
                      size="small"
                      color={camera.is_active ? 'success' : 'default'}
                      variant="outlined"
                      sx={{ fontWeight: 500 }}
                    />
                  </Paper>
                ))
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <VideocamOffIcon sx={{ fontSize: 40, color: 'text.secondary', opacity: 0.5, mb: 1 }} />
                  <Typography>Nenhuma câmera encontrada.</Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
