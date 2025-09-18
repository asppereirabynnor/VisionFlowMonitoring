#!/usr/bin/env python3
"""
Script para testar endpoints ONVIF com uma câmera real.
Este script deve ser executado com a aplicação em execução.
"""

import requests
import json
import argparse
import sys
import time

# Configurações padrão
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

def get_token(api_url, username, password):
    """Obtém um token de autenticação."""
    try:
        response = requests.post(
            f"{api_url}/auth/token",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Erro ao obter token: {e}")
        sys.exit(1)

def test_discover_devices(api_url, token):
    """Testa a descoberta de dispositivos ONVIF na rede."""
    print("\n--- Testando descoberta de dispositivos ONVIF ---")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{api_url}/onvif/discover", headers=headers)
        response.raise_for_status()
        devices = response.json()
        
        if not devices:
            print("Nenhum dispositivo ONVIF encontrado na rede.")
            return None
        
        print(f"Encontrados {len(devices)} dispositivos ONVIF:")
        for i, device in enumerate(devices):
            print(f"{i+1}. Endereço: {device['xaddrs'][0]}")
        
        return devices
    except Exception as e:
        print(f"Erro ao descobrir dispositivos: {e}")
        return None

def test_add_camera(api_url, token, onvif_url, name="Test Camera", rtsp_url=None):
    """Adiciona uma câmera com URL ONVIF."""
    print(f"\n--- Adicionando câmera ONVIF: {name} ---")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        camera_data = {
            "name": name,
            "url": rtsp_url or "rtsp://example.com/stream",
            "username": "admin",
            "password": "admin",
            "onvif_url": onvif_url,
            "enabled": True
        }
        
        response = requests.post(
            f"{api_url}/cameras",
            headers=headers,
            json=camera_data
        )
        response.raise_for_status()
        camera = response.json()
        print(f"Câmera adicionada com sucesso. ID: {camera['id']}")
        return camera
    except Exception as e:
        print(f"Erro ao adicionar câmera: {e}")
        return None

def test_get_device_info(api_url, token, camera_id):
    """Testa a obtenção de informações do dispositivo."""
    print(f"\n--- Obtendo informações do dispositivo para câmera {camera_id} ---")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{api_url}/onvif/cameras/{camera_id}/info",
            headers=headers
        )
        response.raise_for_status()
        info = response.json()
        print(json.dumps(info, indent=2))
        return info
    except Exception as e:
        print(f"Erro ao obter informações do dispositivo: {e}")
        return None

def test_get_capabilities(api_url, token, camera_id):
    """Testa a obtenção de capacidades do dispositivo."""
    print(f"\n--- Obtendo capacidades do dispositivo para câmera {camera_id} ---")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{api_url}/onvif/cameras/{camera_id}/capabilities",
            headers=headers
        )
        response.raise_for_status()
        capabilities = response.json()
        print(json.dumps(capabilities, indent=2))
        return capabilities
    except Exception as e:
        print(f"Erro ao obter capacidades do dispositivo: {e}")
        return None

def test_ptz_control(api_url, token, camera_id):
    """Testa o controle PTZ."""
    print(f"\n--- Testando controle PTZ para câmera {camera_id} ---")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Movimento para a direita
        print("Movendo para a direita...")
        response = requests.post(
            f"{api_url}/onvif/cameras/{camera_id}/ptz",
            headers=headers,
            json={"pan": 0.5, "tilt": 0.0, "zoom": 0.0, "mode": "continuous"}
        )
        response.raise_for_status()
        print("Movimento iniciado.")
        
        # Aguarda 2 segundos
        time.sleep(2)
        
        # Para o movimento
        print("Parando movimento...")
        response = requests.post(
            f"{api_url}/onvif/cameras/{camera_id}/ptz",
            headers=headers,
            json={"mode": "stop"}
        )
        response.raise_for_status()
        print("Movimento parado.")
        
        # Movimento para a esquerda
        print("Movendo para a esquerda...")
        response = requests.post(
            f"{api_url}/onvif/cameras/{camera_id}/ptz",
            headers=headers,
            json={"pan": -0.5, "tilt": 0.0, "zoom": 0.0, "mode": "continuous"}
        )
        response.raise_for_status()
        print("Movimento iniciado.")
        
        # Aguarda 2 segundos
        time.sleep(2)
        
        # Para o movimento
        print("Parando movimento...")
        response = requests.post(
            f"{api_url}/onvif/cameras/{camera_id}/ptz",
            headers=headers,
            json={"mode": "stop"}
        )
        response.raise_for_status()
        print("Movimento parado.")
        
        return True
    except Exception as e:
        print(f"Erro ao testar controle PTZ: {e}")
        return False

def test_presets(api_url, token, camera_id):
    """Testa a criação, listagem e uso de presets."""
    print(f"\n--- Testando presets para câmera {camera_id} ---")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Listar presets existentes
        print("Listando presets existentes...")
        response = requests.get(
            f"{api_url}/onvif/cameras/{camera_id}/presets",
            headers=headers
        )
        response.raise_for_status()
        existing_presets = response.json()
        print(f"Encontrados {len(existing_presets)} presets existentes.")
        
        # Criar um novo preset
        print("Criando novo preset...")
        response = requests.post(
            f"{api_url}/onvif/cameras/{camera_id}/presets",
            headers=headers,
            json={"name": "Test Preset", "description": "Preset criado pelo script de teste"}
        )
        response.raise_for_status()
        new_preset = response.json()
        print(f"Preset criado com sucesso. ID: {new_preset['id']}")
        
        # Listar presets novamente para confirmar
        print("Listando presets atualizados...")
        response = requests.get(
            f"{api_url}/onvif/cameras/{camera_id}/presets",
            headers=headers
        )
        response.raise_for_status()
        updated_presets = response.json()
        print(f"Agora existem {len(updated_presets)} presets.")
        
        # Ir para o preset criado
        print(f"Indo para o preset {new_preset['id']}...")
        response = requests.post(
            f"{api_url}/onvif/cameras/{camera_id}/presets/{new_preset['id']}/goto",
            headers=headers
        )
        response.raise_for_status()
        print("Comando enviado com sucesso.")
        
        # Aguarda um pouco para a câmera se mover
        time.sleep(3)
        
        # Excluir o preset criado
        print(f"Excluindo o preset {new_preset['id']}...")
        response = requests.delete(
            f"{api_url}/onvif/cameras/{camera_id}/presets/{new_preset['id']}",
            headers=headers
        )
        response.raise_for_status()
        print("Preset excluído com sucesso.")
        
        return True
    except Exception as e:
        print(f"Erro ao testar presets: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Teste de endpoints ONVIF")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="URL da API")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Nome de usuário para autenticação")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Senha para autenticação")
    parser.add_argument("--camera-id", type=int, help="ID da câmera para testar (se já existir)")
    parser.add_argument("--onvif-url", help="URL ONVIF da câmera (se for adicionar uma nova)")
    args = parser.parse_args()
    
    # Obtém token de autenticação
    token = get_token(args.api_url, args.username, args.password)
    print(f"Token de autenticação obtido com sucesso.")
    
    camera_id = args.camera_id
    
    # Se não foi fornecido um ID de câmera, tenta descobrir dispositivos e adicionar um
    if not camera_id:
        if args.onvif_url:
            # Adiciona câmera com a URL ONVIF fornecida
            camera = test_add_camera(args.api_url, token, args.onvif_url)
            if camera:
                camera_id = camera["id"]
        else:
            # Tenta descobrir dispositivos
            devices = test_discover_devices(args.api_url, token)
            if devices:
                # Pergunta ao usuário qual dispositivo usar
                choice = input("\nDigite o número do dispositivo para adicionar (ou 'q' para sair): ")
                if choice.lower() == 'q':
                    sys.exit(0)
                
                try:
                    device_index = int(choice) - 1
                    if 0 <= device_index < len(devices):
                        device = devices[device_index]
                        onvif_url = device["xaddrs"][0]
                        camera = test_add_camera(args.api_url, token, onvif_url)
                        if camera:
                            camera_id = camera["id"]
                    else:
                        print("Escolha inválida.")
                except ValueError:
                    print("Entrada inválida.")
    
    # Se temos um ID de câmera, executa os testes
    if camera_id:
        # Testa obtenção de informações do dispositivo
        test_get_device_info(args.api_url, token, camera_id)
        
        # Testa obtenção de capacidades do dispositivo
        capabilities = test_get_capabilities(args.api_url, token, camera_id)
        
        if capabilities and capabilities.get("ptz", False):
            # Testa controle PTZ
            test_ptz_control(args.api_url, token, camera_id)
            
            # Testa presets
            test_presets(args.api_url, token, camera_id)
        else:
            print("A câmera não suporta PTZ. Pulando testes de PTZ e presets.")
    else:
        print("Nenhuma câmera disponível para teste.")

if __name__ == "__main__":
    main()
