import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.models import Camera, CameraPreset

@pytest.fixture
def mock_onvif_controller():
    """Fixture para criar um mock do controlador ONVIF."""
    with patch('bynnor_smart_monitoring.api.onvif.ONVIFController') as mock:
        controller_instance = MagicMock()
        mock.return_value = controller_instance
        yield controller_instance

@pytest.fixture
def test_camera(db_session):
    """Fixture para criar uma câmera de teste no banco de dados."""
    camera = Camera(
        id=1,
        name="Test Camera",
        url="rtsp://example.com/stream",
        username="admin",
        password="admin",
        onvif_url="http://example.com:8080/onvif/device_service",
        enabled=True
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)
    return camera

@pytest.fixture
def test_preset(db_session, test_camera):
    """Fixture para criar um preset de teste no banco de dados."""
    preset = CameraPreset(
        id=1,
        camera_id=test_camera.id,
        name="Test Preset",
        preset_token="preset_token_1",
        description="Test preset description"
    )
    db_session.add(preset)
    db_session.commit()
    db_session.refresh(preset)
    return preset

def test_get_camera_presets(client, auth_headers, test_camera, test_preset, mock_onvif_controller):
    """Testa o endpoint para listar presets de uma câmera."""
    mock_onvif_controller.get_presets.return_value = [
        {"token": "preset_token_1", "name": "Test Preset", "position": {"x": 0.5, "y": 0.5, "z": 0.0}}
    ]
    
    response = client.get(f"/onvif/cameras/{test_camera.id}/presets", headers=auth_headers)
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test Preset"
    assert response.json()[0]["token"] == "preset_token_1"

def test_create_preset(client, auth_headers, test_camera, mock_onvif_controller):
    """Testa o endpoint para criar um novo preset."""
    mock_onvif_controller.create_preset.return_value = "new_preset_token"
    
    response = client.post(
        f"/onvif/cameras/{test_camera.id}/presets",
        headers=auth_headers,
        json={"name": "New Preset", "description": "New preset description"}
    )
    
    assert response.status_code == 201
    assert response.json()["name"] == "New Preset"
    assert response.json()["preset_token"] == "new_preset_token"
    assert response.json()["description"] == "New preset description"

def test_goto_preset(client, auth_headers, test_camera, test_preset, mock_onvif_controller):
    """Testa o endpoint para mover a câmera para um preset."""
    mock_onvif_controller.goto_preset.return_value = True
    
    response = client.post(
        f"/onvif/cameras/{test_camera.id}/presets/{test_preset.id}/goto",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["success"] == True
    mock_onvif_controller.goto_preset.assert_called_once_with(test_preset.preset_token)

def test_delete_preset(client, auth_headers, test_camera, test_preset, mock_onvif_controller):
    """Testa o endpoint para excluir um preset."""
    mock_onvif_controller.remove_preset.return_value = True
    
    response = client.delete(
        f"/onvif/cameras/{test_camera.id}/presets/{test_preset.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["success"] == True
    mock_onvif_controller.remove_preset.assert_called_once_with(test_preset.preset_token)

def test_ptz_control(client, auth_headers, test_camera, mock_onvif_controller):
    """Testa o endpoint para controle PTZ."""
    mock_onvif_controller.ptz_continuous_move.return_value = True
    
    response = client.post(
        f"/onvif/cameras/{test_camera.id}/ptz",
        headers=auth_headers,
        json={"pan": 0.5, "tilt": -0.3, "zoom": 0.0, "mode": "continuous"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] == True
    mock_onvif_controller.ptz_continuous_move.assert_called_once_with(0.5, -0.3, 0.0)

def test_ptz_stop(client, auth_headers, test_camera, mock_onvif_controller):
    """Testa o endpoint para parar o movimento PTZ."""
    mock_onvif_controller.ptz_stop.return_value = True
    
    response = client.post(
        f"/onvif/cameras/{test_camera.id}/ptz",
        headers=auth_headers,
        json={"mode": "stop"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] == True
    mock_onvif_controller.ptz_stop.assert_called_once()

def test_get_device_info(client, auth_headers, test_camera, mock_onvif_controller):
    """Testa o endpoint para obter informações do dispositivo."""
    mock_onvif_controller.get_device_info.return_value = {
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "firmware_version": "1.0.0",
        "serial_number": "123456789",
        "hardware_id": "HW123"
    }
    
    response = client.get(f"/onvif/cameras/{test_camera.id}/info", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["manufacturer"] == "Test Manufacturer"
    assert response.json()["model"] == "Test Model"

def test_get_capabilities(client, auth_headers, test_camera, mock_onvif_controller):
    """Testa o endpoint para obter capacidades do dispositivo."""
    mock_onvif_controller.get_capabilities.return_value = {
        "ptz": True,
        "events": True,
        "imaging": True,
        "media": True,
        "analytics": False
    }
    
    response = client.get(f"/onvif/cameras/{test_camera.id}/capabilities", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["ptz"] == True
    assert response.json()["analytics"] == False

def test_discover_devices(client, auth_headers, mock_onvif_controller):
    """Testa o endpoint para descobrir dispositivos ONVIF na rede."""
    mock_onvif_controller.discover_devices.return_value = [
        {
            "xaddrs": ["http://192.168.1.100:8080/onvif/device_service"],
            "types": ["dn:NetworkVideoTransmitter"],
            "scopes": ["onvif://www.onvif.org/name/TestCamera"]
        }
    ]
    
    response = client.post("/onvif/discover", headers=auth_headers)
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "http://192.168.1.100:8080/onvif/device_service" in response.json()[0]["xaddrs"]
