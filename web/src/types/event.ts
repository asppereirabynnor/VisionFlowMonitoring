export interface EventResponse {
  id?: number;
  camera_id?: number;
  camera_name?: string;
  type: string | object;
  confidence?: number;
  timestamp: string;
  created_at?: string;
  image_path?: string;
  video_path?: string;
  event_metadata?: string;
}
