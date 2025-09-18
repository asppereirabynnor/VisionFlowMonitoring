import axios from 'axios';
import { format, startOfDay, endOfDay } from 'date-fns';
import { EventResponse } from '../types/event';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Interfaces
export interface Event {
  id: number;
  camera_id: number;
  camera_name: string;
  event_type: string;
  confidence: number;
  timestamp: string;
  image_path: string;
  video_path?: string;
  metadata?: any;
}

export interface EventFilter {
  camera_id?: number;
  event_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

// Funções auxiliares
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    headers: {
      Authorization: `Bearer ${token}`
    }
  };
};

// Funções de API
export const getEvents = async (filter?: EventFilter): Promise<Event[]> => {
  const params = filter || {};
  const response = await axios.get(`${API_URL}/events`, {
    ...getAuthHeaders(),
    params
  });
  
  // Mapear os campos do backend para o frontend
  return response.data.map((event: any) => ({
    ...event,
    // Se type for um objeto com valor, extrair o valor, caso contrário usar o próprio type
    event_type: typeof event.type === 'object' && event.type !== null ? 
      (event.type.value || event.type) : event.type,
    timestamp: event.created_at,  // Mapear 'created_at' para 'timestamp'
    metadata: event.event_metadata ? JSON.parse(event.event_metadata) : undefined  // Converter metadata de string para objeto
  }));
};

export const getEvent = async (id: number): Promise<Event> => {
  const response = await axios.get(`${API_URL}/events/${id}`, getAuthHeaders());
  
  // Mapear os campos do backend para o frontend
  const event = response.data;
  return {
    ...event,
    // Se type for um objeto com valor, extrair o valor, caso contrário usar o próprio type
    event_type: typeof event.type === 'object' && event.type !== null ? 
      (event.type.value || event.type) : event.type,
    timestamp: event.created_at,  // Mapear 'created_at' para 'timestamp'
    metadata: event.event_metadata ? JSON.parse(event.event_metadata) : undefined  // Converter metadata de string para objeto
  };
};

export const getEventTypes = async (): Promise<string[]> => {
  const response = await axios.get(`${API_URL}/events/types`, getAuthHeaders());
  return response.data;
};

export const getEventStats = async (filter?: EventFilter): Promise<any> => {
  const params = filter || {};
  const response = await axios.get(`${API_URL}/events/stats/summary`, {
    ...getAuthHeaders(),
    params
  });
  return response.data;
};

export const getEventsToday = async (): Promise<EventResponse[]> => {
  const today = new Date();
  const start = startOfDay(today);
  const end = endOfDay(today);
  
  const filter: EventFilter = {
    start_date: format(start, 'yyyy-MM-dd\'T\'HH:mm:ss'),
    end_date: format(end, 'yyyy-MM-dd\'T\'HH:mm:ss')
  };
  
  const events = await getEvents(filter);
  
  // Converter de Event para EventResponse
  return events.map(event => ({
    id: event.id,
    camera_id: event.camera_id,
    camera_name: event.camera_name,
    type: event.event_type,
    confidence: event.confidence,
    timestamp: event.timestamp,
    image_path: event.image_path,
    video_path: event.video_path,
    event_metadata: event.metadata ? JSON.stringify(event.metadata) : undefined
  }));
};
