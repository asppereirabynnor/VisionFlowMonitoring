import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Interfaces
export interface Camera {
  id: number;
  name: string;
  rtsp_url: string;
  ip_address: string;
  port: number;
  username: string;
  password: string;
  onvif_url: string;
  description: string;
  location: string;
  model: string;
  manufacturer: string;
  is_active: boolean;
  status: string;
  last_online: string;
  created_at: string;
  updated_at: string;
  screenshot_base64?: string;
}

export interface CameraPreset {
  id: number;
  camera_id: number;
  name: string;
  preset_token: string;
  description?: string;
  created_at: string;
}

export interface DeviceInfo {
  manufacturer: string;
  model: string;
  firmware_version: string;
  serial_number: string;
  hardware_id: string;
}

export interface Capabilities {
  ptz: boolean;
  events: boolean;
  imaging: boolean;
  media: boolean;
  analytics: boolean;
}

export interface PTZCommand {
  pan: number;
  tilt: number;
  zoom: number;
  mode: 'continuous' | 'absolute' | 'relative' | 'stop';
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
export const getCameras = async (): Promise<Camera[]> => {
  const response = await axios.get(`${API_URL}/cameras/`, getAuthHeaders());
  return response.data;
};

export const getCamera = async (id: number): Promise<Camera> => {
  const response = await axios.get(`${API_URL}/cameras/${id}/`, getAuthHeaders());
  return response.data;
};

export const createCamera = async (camera: Omit<Camera, 'id' | 'created_at' | 'updated_at' | 'status' | 'last_online'>): Promise<Camera> => {
  const response = await axios.post(`${API_URL}/cameras/`, camera, getAuthHeaders());
  return response.data;
};

export const updateCamera = async (id: number, camera: Partial<Camera>): Promise<Camera> => {
  const response = await axios.put(`${API_URL}/cameras/${id}/`, camera, getAuthHeaders());
  return response.data;
};

export const deleteCamera = async (id: number): Promise<void> => {
  await axios.delete(`${API_URL}/cameras/${id}/`, getAuthHeaders());
};

// Funções ONVIF
export const getCameraPresets = async (cameraId: number): Promise<CameraPreset[]> => {
  const response = await axios.get(`${API_URL}/onvif/cameras/${cameraId}/presets`, getAuthHeaders());
  return response.data;
};

export const createPreset = async (cameraId: number, name: string, description?: string): Promise<CameraPreset> => {
  const response = await axios.post(
    `${API_URL}/onvif/cameras/${cameraId}/presets`, 
    { name, description },
    getAuthHeaders()
  );
  return response.data;
};

export const gotoPreset = async (cameraId: number, presetId: number): Promise<{ success: boolean }> => {
  const response = await axios.post(
    `${API_URL}/onvif/cameras/${cameraId}/presets/${presetId}/goto`,
    {},
    getAuthHeaders()
  );
  return response.data;
};

export const deletePreset = async (cameraId: number, presetId: number): Promise<{ success: boolean }> => {
  const response = await axios.delete(
    `${API_URL}/onvif/cameras/${cameraId}/presets/${presetId}`,
    getAuthHeaders()
  );
  return response.data;
};

export const controlPTZ = async (cameraId: number, command: PTZCommand): Promise<{ success: boolean }> => {
  const response = await axios.post(
    `${API_URL}/onvif/cameras/${cameraId}/ptz`,
    command,
    getAuthHeaders()
  );
  return response.data;
};

export const stopPTZ = async (cameraId: number): Promise<{ success: boolean }> => {
  return controlPTZ(cameraId, { pan: 0, tilt: 0, zoom: 0, mode: 'stop' });
};

export const getDeviceInfo = async (cameraId: number): Promise<DeviceInfo> => {
  const response = await axios.get(`${API_URL}/onvif/cameras/${cameraId}/info`, getAuthHeaders());
  return response.data;
};

export const getCapabilities = async (cameraId: number): Promise<Capabilities> => {
  const response = await axios.get(`${API_URL}/onvif/cameras/${cameraId}/capabilities`, getAuthHeaders());
  return response.data;
};

export const discoverDevices = async (): Promise<any[]> => {
  const response = await axios.post(`${API_URL}/onvif/discover`, {}, getAuthHeaders());
  return response.data;
};

export const updateCameraScreenshot = async (cameraId: number, screenshot_base64: string): Promise<Camera> => {
  console.log(`Enviando screenshot para câmera ${cameraId}`);
  console.log(`URL da API: ${API_URL}/cameras/${cameraId}/screenshot`);
  
  // Garantir que o screenshot_base64 seja uma string válida
  if (!screenshot_base64 || typeof screenshot_base64 !== 'string') {
    throw new Error('screenshot_base64 inválido');
  }
  
  try {
    const response = await axios.post(
      `${API_URL}/cameras/${cameraId}/screenshot`,
      { screenshot_base64 },
      getAuthHeaders()
    );
    console.log('Resposta da API de screenshot:', response.status);
    return response.data;
  } catch (error: any) {
    console.error('Erro ao enviar screenshot:', error.response?.data || error.message);
    throw error;
  }
};
