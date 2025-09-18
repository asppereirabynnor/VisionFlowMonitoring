import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardMedia,
  Chip,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Pagination,
  Paper,
  Select,
  SelectChangeEvent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useQuery } from '@tanstack/react-query';
import { getEvents, getEventTypes, Event, EventFilter } from '../services/eventService';
import { getCameras } from '../services/cameraService';
import EventTypeCharts from '../components/EventTypeCharts';

const EventList: React.FC = () => {
  const [page, setPage] = useState(1);
  const [rowsPerPage] = useState(10);
  const [filter, setFilter] = useState<EventFilter>({
    limit: rowsPerPage,
    offset: 0,
  });
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [openDialog, setOpenDialog] = useState(false);

  // Queries
  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['events', filter],
    queryFn: () => getEvents(filter),
  });

  const { data: eventTypes, isLoading: eventTypesLoading } = useQuery({
    queryKey: ['eventTypes'],
    queryFn: getEventTypes,
  });

  const { data: cameras, isLoading: camerasLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: getCameras,
  });

  // Handlers
  const handleChangePage = (event: React.ChangeEvent<unknown>, value: number) => {
    const newOffset = (value - 1) * rowsPerPage;
    setPage(value);
    setFilter({
      ...filter,
      offset: newOffset,
    });
  };

  const handleFilterChange = (name: keyof EventFilter, value: any) => {
    setFilter({
      ...filter,
      [name]: value,
      offset: 0, // Reset pagination when filter changes
    });
    setPage(1);
  };

  const handleCameraChange = (event: SelectChangeEvent<number>) => {
    const value = event.target.value;
    handleFilterChange('camera_id', value === 0 ? undefined : value);
  };

  const handleEventTypeChange = (event: SelectChangeEvent<string>) => {
    const value = event.target.value;
    handleFilterChange('event_type', value === 'all' ? undefined : value);
  };

  const handleStartDateChange = (date: Date | null) => {
    if (date) {
      handleFilterChange('start_date', date.toISOString().split('T')[0]);
    } else {
      const { start_date, ...rest } = filter;
      setFilter(rest);
    }
  };

  const handleEndDateChange = (date: Date | null) => {
    if (date) {
      handleFilterChange('end_date', date.toISOString().split('T')[0]);
    } else {
      const { end_date, ...rest } = filter;
      setFilter(rest);
    }
  };

  const handleEventClick = (event: Event) => {
    setSelectedEvent(event);
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const isLoading = eventsLoading || eventTypesLoading || camerasLoading;

  return (
    <Box sx={{ flexGrow: 1 }}>
      {events && events.length > 0 && (
        <EventTypeCharts events={events} />
      )}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel id="camera-filter-label">Câmera</InputLabel>
              <Select
                labelId="camera-filter-label"
                id="camera-filter"
                value={filter.camera_id || 0}
                label="Câmera"
                onChange={handleCameraChange}
              >
                <MenuItem value={0}>Todas</MenuItem>
                {cameras?.map((camera) => (
                  <MenuItem key={camera.id} value={camera.id}>
                    {camera.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel id="event-type-filter-label">Tipo de Evento</InputLabel>
              <Select
                labelId="event-type-filter-label"
                id="event-type-filter"
                value={filter.event_type || 'all'}
                label="Tipo de Evento"
                onChange={handleEventTypeChange}
              >
                <MenuItem value="all">Todos</MenuItem>
                {eventTypes?.map((type) => (
                  <MenuItem key={type} value={type}>
                    {type}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <Grid item xs={12} sm={6} md={3}>
              <DatePicker
                label="Data Inicial"
                value={filter.start_date ? new Date(filter.start_date) : null}
                onChange={handleStartDateChange}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DatePicker
                label="Data Final"
                value={filter.end_date ? new Date(filter.end_date) : null}
                onChange={handleEndDateChange}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </Grid>
          </LocalizationProvider>
        </Grid>
      </Paper>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="eventos">
              <TableHead>
                <TableRow>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Câmera</TableCell>
                  <TableCell>Data/Hora</TableCell>
                  <TableCell>Confiança</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {events && events.length > 0 ? (
                  events.map((event) => (
                    <TableRow
                      key={event.id}
                      hover
                      onClick={() => handleEventClick(event)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>
                        <Chip label={event.event_type || 'Desconhecido'} color="primary" />
                      </TableCell>
                      <TableCell>{event.camera_name || `Câmera ${event.camera_id || 'Desconhecida'}`}</TableCell>
                      <TableCell>
                        {event.timestamp && !isNaN(new Date(event.timestamp).getTime()) ? 
                          new Date(event.timestamp).toLocaleString() : 
                          'Data não disponível'}
                      </TableCell>
                      <TableCell>
                        {event.confidence !== undefined ? 
                          ((event.confidence > 1 ? event.confidence / 100 : event.confidence) * 100).toFixed(1) + '%' : 
                          'N/A'}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      Nenhum evento encontrado com os filtros selecionados.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Pagination
              count={Math.ceil((events?.length || 0) / rowsPerPage)}
              page={page}
              onChange={handleChangePage}
              color="primary"
            />
          </Box>
        </>
      )}

      {/* Diálogo de detalhes do evento */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        {selectedEvent && (
          <>
            <DialogTitle>
              Detalhes do Evento: {selectedEvent.event_type || 'Desconhecido'}
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardMedia
                      component="img"
                      height="300"
                      image={selectedEvent.image_path || '/placeholder-image.jpg'}
                      alt="Imagem do evento"
                      sx={{ objectFit: 'contain', bgcolor: 'black' }}
                    />
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Informações do Evento
                      </Typography>
                      <Typography variant="body1">
                        <strong>ID:</strong> {selectedEvent.id || 'N/A'}
                      </Typography>
                      <Typography variant="body1">
                        <strong>Tipo:</strong> {selectedEvent.event_type || 'Desconhecido'}
                      </Typography>
                      <Typography variant="body1">
                        <strong>Câmera:</strong> {selectedEvent.camera_name || `Câmera ${selectedEvent.camera_id || 'Desconhecida'}`}
                      </Typography>
                      <Typography variant="body1">
                        <strong>Data/Hora:</strong>{' '}
                        {selectedEvent.timestamp && !isNaN(new Date(selectedEvent.timestamp).getTime()) ? 
                          new Date(selectedEvent.timestamp).toLocaleString() : 
                          'Data não disponível'}
                      </Typography>
                      <Typography variant="body1">
                        <strong>Confiança:</strong>{' '}
                        {selectedEvent.confidence !== undefined ? 
                          `${((selectedEvent.confidence > 1 ? selectedEvent.confidence / 100 : selectedEvent.confidence) * 100).toFixed(1)}%` : 
                          'N/A'}
                      </Typography>
                      {selectedEvent.video_path && (
                        <Typography variant="body1">
                          <strong>Vídeo:</strong> Disponível
                        </Typography>
                      )}
                      {selectedEvent.metadata && (
                        <>
                          <Typography variant="body1" sx={{ mt: 2 }}>
                            <strong>Metadados:</strong>
                          </Typography>
                          <Box
                            component="pre"
                            sx={{
                              bgcolor: 'grey.100',
                              p: 1,
                              borderRadius: 1,
                              overflow: 'auto',
                              maxHeight: 200,
                            }}
                          >
                            {JSON.stringify(selectedEvent.metadata, null, 2)}
                          </Box>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default EventList;
