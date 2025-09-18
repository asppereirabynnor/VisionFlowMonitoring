from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from db.base import Base

class UserRole(str, PyEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean(), default=True)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    cameras = relationship("Camera", back_populates="owner")
    events = relationship("Event", back_populates="created_by")

class CameraStatus(str, PyEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    rtsp_url = Column(String, nullable=False)
    onvif_url = Column(String)  # URL para o serviço ONVIF (ex: http://192.168.1.100:8000)
    ip_address = Column(String, nullable=False)
    port = Column(Integer, default=554)
    username = Column(String)
    password = Column(String)  # Deve ser criptografado em produção
    status = Column(Enum(CameraStatus), default=CameraStatus.OFFLINE)
    is_active = Column(Boolean, default=True)
    location = Column(String)
    model = Column(String)
    manufacturer = Column(String)
    last_seen = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    screenshot_base64 = Column(Text)  # Armazena a imagem em base64 para simulação

    # Relacionamentos
    owner = relationship("User", back_populates="cameras")
    events = relationship("Event", back_populates="camera")
    presets = relationship("CameraPreset", back_populates="camera")

class EventType(str, PyEnum):
    MOTION = "motion"
    PERSON = "person"
    VEHICLE = "vehicle"
    OBJECT = "object"
    ALERT = "alert"
    SYSTEM = "system"

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(EventType), nullable=False)
    description = Column(String)
    confidence = Column(Integer)  # 0-100
    event_metadata = Column(Text)  # Detalhes adicionais do evento (armazenado como JSON string)
    image_path = Column(String)  # Caminho para a imagem do evento
    video_path = Column(String)  # Caminho para o vídeo do evento (se aplicável)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    created_by_id = Column(Integer, ForeignKey("users.id"))

    # Relacionamentos
    camera = relationship("Camera", back_populates="events")
    created_by = relationship("User", back_populates="events")

class CameraPreset(Base):
    __tablename__ = "camera_presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    preset_token = Column(String, nullable=False)  # Token do preset na câmera
    position = Column(Text, nullable=True)  # Armazena a posição PTZ como JSON string
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    camera = relationship("Camera", back_populates="presets")
