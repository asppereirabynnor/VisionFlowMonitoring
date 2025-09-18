import React, { useState, useEffect } from 'react';
import {
  Badge,
  IconButton,
  Popover,
  List,
  ListItem,
  ListItemText,
  Typography,
  Box,
  Divider,
  Paper,
} from '@mui/material';
import { Notifications as NotificationsIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { getEventsToday } from '../services/eventService';
import { EventResponse } from '../types/event';

const NotificationBell: React.FC = () => {
  const [notifications, setNotifications] = useState<EventResponse[]>([]);
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const todayEvents = await getEventsToday();
      setNotifications(todayEvents);
    } catch (error) {
      console.error('Erro ao buscar notificações:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    
    // Atualizar notificações a cada 5 minutos
    const interval = setInterval(() => {
      fetchNotifications();
    }, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);
  const id = open ? 'notifications-popover' : undefined;

  // Função para formatar o tipo de evento
  const formatEventType = (type: string | object): string => {
    if (typeof type === 'object' && type !== null) {
      // Se for um objeto, tenta extrair o valor do enum
      return (type as any).event_type || 'Desconhecido';
    }
    return type || 'Desconhecido';
  };

  // Função para formatar a data
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return format(date, "dd/MM/yyyy 'às' HH:mm", { locale: ptBR });
    } catch (error) {
      return 'Data inválida';
    }
  };

  return (
    <>
      <IconButton
        color="inherit"
        aria-label="notificações"
        onClick={handleClick}
        size="large"
      >
        <Badge badgeContent={notifications.length} color="error">
          <NotificationsIcon />
        </Badge>
      </IconButton>
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <Paper sx={{ width: 350, maxHeight: 400, overflow: 'auto', bgcolor: 'background.paper' }}>
          <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'white' }}>
            <Typography variant="h6">Notificações de Hoje</Typography>
          </Box>
          <List sx={{ p: 0 }}>
            {loading ? (
              <ListItem>
                <ListItemText primary="Carregando notificações..." />
              </ListItem>
            ) : notifications.length > 0 ? (
              notifications.map((notification, index) => (
                <React.Fragment key={notification.id || index}>
                  <ListItem alignItems="flex-start">
                    <ListItemText
                      primary={
                        <Typography variant="subtitle1" color="text.primary">
                          {formatEventType(notification.type)}
                        </Typography>
                      }
                      secondary={
                        <React.Fragment>
                          <Typography
                            component="span"
                            variant="body2"
                            color="text.primary"
                          >
                            Câmera: {notification.camera_name || 'Desconhecida'}
                          </Typography>
                          <br />
                          <Typography
                            component="span"
                            variant="body2"
                            color="text.secondary"
                          >
                            {formatDate(notification.timestamp)}
                          </Typography>
                        </React.Fragment>
                      }
                    />
                  </ListItem>
                  {index < notifications.length - 1 && <Divider />}
                </React.Fragment>
              ))
            ) : (
              <ListItem>
                <ListItemText primary="Nenhuma notificação hoje" />
              </ListItem>
            )}
          </List>
        </Paper>
      </Popover>
    </>
  );
};

export default NotificationBell;
