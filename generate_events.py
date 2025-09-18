#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para gerar massa de dados de eventos para o sistema Bynnor Smart Monitoring.
Cria eventos no passado e para o dia de hoje com diferentes tipos e níveis de confiança.
"""

import random
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Event, EventType, Camera, User
from db.base import Base, SessionLocal

def generate_random_events(session, num_events=100):
    """
    Gera eventos aleatórios para as câmeras existentes.
    
    Args:
        session: Sessão do SQLAlchemy
        num_events: Número de eventos a serem gerados
    """
    # Buscar câmeras e usuários existentes
    cameras = session.query(Camera).all()
    users = session.query(User).all()
    
    if not cameras:
        print("Erro: Nenhuma câmera encontrada no sistema.")
        return
    
    if not users:
        print("Erro: Nenhum usuário encontrado no sistema.")
        return
    
    print(f"Gerando {num_events} eventos aleatórios...")
    
    # Tipos de eventos disponíveis
    event_types = [
        EventType.MOTION,
        EventType.PERSON,
        EventType.VEHICLE,
        EventType.OBJECT,
        EventType.ALERT,
        EventType.SYSTEM
    ]
    
    # Descrições para cada tipo de evento
    descriptions = {
        EventType.MOTION: ["Movimento detectado", "Atividade detectada", "Movimento na área restrita"],
        EventType.PERSON: ["Pessoa detectada", "Indivíduo não autorizado", "Pessoa na área de segurança"],
        EventType.VEHICLE: ["Veículo detectado", "Carro estacionado em área proibida", "Veículo suspeito"],
        EventType.OBJECT: ["Objeto abandonado", "Item suspeito detectado", "Objeto removido"],
        EventType.ALERT: ["Alerta de segurança", "Violação de perímetro", "Alerta de intrusão"],
        EventType.SYSTEM: ["Falha na câmera", "Reinicialização do sistema", "Perda de conexão"]
    }
    
    # Gerar eventos distribuídos nos últimos 30 dias até hoje
    now = datetime.now()
    start_date = now - timedelta(days=30)
    
    # Distribuir eventos ao longo do período
    events_created = 0
    
    for _ in range(num_events):
        # Selecionar câmera e usuário aleatórios
        camera = random.choice(cameras)
        user = random.choice(users)
        
        # Selecionar tipo de evento aleatório
        event_type = random.choice(event_types)
        
        # Selecionar descrição aleatória para o tipo de evento
        description = random.choice(descriptions[event_type])
        
        # Gerar confiança aleatória (0-100)
        confidence = random.randint(50, 100)
        
        # Gerar data aleatória nos últimos 30 dias
        random_days = random.randint(0, 30)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        event_date = now - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        
        # Gerar metadados do evento
        metadata = {
            "coordinates": {
                "x": random.randint(10, 1270),
                "y": random.randint(10, 710)
            },
            "size": {
                "width": random.randint(50, 200),
                "height": random.randint(50, 200)
            },
            "duration": random.randint(1, 60),  # duração em segundos
            "tags": random.sample(["movimento", "segurança", "alerta", "detecção", "perímetro"], 
                                 k=random.randint(1, 3))
        }
        
        # Criar evento
        event = Event(
            type=event_type,
            description=description,
            confidence=confidence,
            event_metadata=json.dumps(metadata),
            image_path=f"/static/events/event_{camera.id}_{event_date.strftime('%Y%m%d%H%M%S')}.jpg",
            created_at=event_date,
            camera_id=camera.id,
            created_by_id=user.id
        )
        
        session.add(event)
        events_created += 1
        
        # Commit a cada 20 eventos para evitar problemas de memória
        if events_created % 20 == 0:
            session.commit()
            print(f"Progresso: {events_created}/{num_events} eventos criados")
    
    # Commit final
    session.commit()
    print(f"Total de {events_created} eventos gerados com sucesso!")

def generate_today_events(session, num_events=20):
    """
    Gera eventos específicos para o dia de hoje.
    
    Args:
        session: Sessão do SQLAlchemy
        num_events: Número de eventos a serem gerados
    """
    # Buscar câmeras e usuários existentes
    cameras = session.query(Camera).all()
    users = session.query(User).all()
    
    if not cameras or not users:
        print("Erro: Câmeras ou usuários não encontrados.")
        return
    
    print(f"Gerando {num_events} eventos para hoje...")
    
    # Data de hoje
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Distribuir eventos ao longo do dia de hoje
    for i in range(num_events):
        # Selecionar câmera e usuário aleatórios
        camera = random.choice(cameras)
        user = random.choice(users)
        
        # Distribuir eventos ao longo do dia
        hours_passed = int((i / num_events) * 24)
        minutes_random = random.randint(0, 59)
        event_time = today + timedelta(hours=hours_passed, minutes=minutes_random)
        
        # Se o horário gerado for no futuro, ajustar para o momento atual
        if event_time > datetime.now():
            event_time = datetime.now() - timedelta(minutes=random.randint(5, 30))
        
        # Determinar tipo de evento com maior probabilidade para pessoas e veículos
        event_type_weights = [
            (EventType.PERSON, 0.4),
            (EventType.VEHICLE, 0.3),
            (EventType.MOTION, 0.15),
            (EventType.OBJECT, 0.1),
            (EventType.ALERT, 0.03),
            (EventType.SYSTEM, 0.02)
        ]
        
        event_type = random.choices(
            [et[0] for et in event_type_weights],
            weights=[et[1] for et in event_type_weights],
            k=1
        )[0]
        
        # Descrições específicas para eventos de hoje
        if event_type == EventType.PERSON:
            descriptions = [
                "Pessoa detectada na entrada principal",
                "Indivíduo na área restrita",
                "Pessoa não autorizada detectada",
                "Funcionário identificado"
            ]
        elif event_type == EventType.VEHICLE:
            descriptions = [
                "Veículo entrando no estacionamento",
                "Carro estacionado em local proibido",
                "Veículo suspeito detectado",
                "Caminhão de entrega na doca"
            ]
        else:
            descriptions = [
                "Movimento detectado no setor A",
                "Objeto abandonado na recepção",
                "Alerta de segurança no perímetro",
                "Atividade suspeita detectada"
            ]
        
        description = random.choice(descriptions)
        
        # Confiança mais alta para eventos recentes
        confidence = random.randint(70, 98)
        
        # Metadados mais detalhados para eventos de hoje
        metadata = {
            "coordinates": {
                "x": random.randint(10, 1270),
                "y": random.randint(10, 710)
            },
            "size": {
                "width": random.randint(50, 200),
                "height": random.randint(50, 200)
            },
            "duration": random.randint(3, 45),
            "tags": random.sample(["hoje", "segurança", "monitoramento", "detecção", "alerta"], 
                                k=random.randint(2, 4)),
            "area": random.choice(["Entrada", "Estacionamento", "Perímetro", "Área Interna", "Recepção"]),
            "priority": random.choice(["Alta", "Média", "Baixa"])
        }
        
        # Criar evento
        event = Event(
            type=event_type,
            description=description,
            confidence=confidence,
            event_metadata=json.dumps(metadata),
            image_path=f"/static/events/today_event_{camera.id}_{event_time.strftime('%Y%m%d%H%M%S')}.jpg",
            created_at=event_time,
            camera_id=camera.id,
            created_by_id=user.id
        )
        
        session.add(event)
    
    session.commit()
    print(f"{num_events} eventos para hoje gerados com sucesso!")

def main():
    """Função principal para gerar eventos."""
    try:
        # Criar sessão do banco de dados
        session = SessionLocal()
        
        # Verificar se já existem muitos eventos no banco
        existing_events = session.query(Event).count()
        print(f"Eventos existentes no banco: {existing_events}")
        
        if existing_events > 500:
            response = input("Já existem muitos eventos no banco. Deseja continuar? (s/n): ")
            if response.lower() != 's':
                print("Operação cancelada pelo usuário.")
                return
        
        # Gerar eventos passados
        generate_random_events(session, num_events=200)
        
        # Gerar eventos para hoje
        generate_today_events(session, num_events=50)
        
        print("Geração de eventos concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro ao gerar eventos: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
