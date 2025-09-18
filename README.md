# VisionFlow Monitoring

Sistema de monitoramento inteligente com câmeras IP, utilizando processamento de vídeo em tempo real com IA para detecção de objetos e eventos.

## 🚀 Funcionalidades

### Gerenciamento de Câmeras
- Conexão com múltiplas câmeras IP via RTSP
- Controle PTZ (Pan-Tilt-Zoom) via ONVIF
- Criação e gerenciamento de presets de posição
- Descoberta automática de dispositivos ONVIF na rede
- Estatísticas de desempenho das câmeras em tempo real

### Detecção e Eventos
- Detecção de objetos em tempo real com YOLOv8
- Gravação automática de eventos com buffer pré e pós-evento
- Geração de miniaturas para eventos detectados
- Filtragem e busca avançada de eventos
- Estatísticas e relatórios de eventos

### Comunicação e Interface
- Notificações em tempo real via WebSocket
- Streaming de vídeo em tempo real para o frontend
- API RESTful completa para integração com outros sistemas
- Interface web responsiva (em desenvolvimento)

### Segurança e Usuários
- Autenticação baseada em JWT
- Controle de acesso baseado em funções (admin, operador, visualizador)
- Gerenciamento de usuários com diferentes níveis de permissão

## 🛠️ Tecnologias

- **Backend**: Python 3.10, FastAPI, SQLAlchemy, Alembic
- **IA e Visão Computacional**: OpenCV, YOLOv8, Ultralytics
- **Banco de Dados**: SQLite (para facilitar a implantação)
- **Frontend**: React, TypeScript, Material-UI
- **Infraestrutura**: Docker, Docker Compose
- **Monitoramento**: Prometheus, Grafana (opcional)

## 🚀 Como Executar

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.10+ (para desenvolvimento local)
- Node.js 16+ (para o frontend)
- PostgreSQL 14+ (se executando fora do Docker)

### Configuração

1. Clone o repositório:
   ```bash
   git clone https://github.com/asppereirabynnor/VisionFlowMonitoring.git
   cd VisionFlowMonitoring
   ```

2. Crie um arquivo `.env` baseado no `.env.example` e configure as variáveis de ambiente necessárias:
   ```
   # Configuração do Banco de Dados
   DATABASE_URL=sqlite:///./data/bynnor.db
   
   # Configuração da API
   HOST=0.0.0.0
   PORT=8000
   DEBUG=True
   
   # Configuração de Segurança
   JWT_SECRET=sua_chave_secreta_aqui
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   
   # Configuração do YOLOv8
   YOLO_MODEL_PATH=yolov8n.pt
   CONFIDENCE_THRESHOLD=0.5
   
   # Configuração de Gravação
   RECORDING_PATH=./static/recordings
   PRE_EVENT_BUFFER_SECONDS=5
   POST_EVENT_BUFFER_SECONDS=5
   ```

3. Instale as dependências (desenvolvimento local):
   ```bash
   pip install -r requirements.txt
   ```

4. Execute as migrações do banco de dados:
   ```bash
   alembic upgrade head
   ```

5. Inicie a aplicação:
   
   **Com Docker Compose:**
   ```bash
   docker-compose up -d
   ```
   
   **Localmente:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Acesse a aplicação:
   - API: http://localhost:8000
   - Documentação da API: http://localhost:8000/docs
   - Interface Web: http://localhost:3000 (quando implementada)

## 👷‍♂️ Estrutura do Projeto

```
bynnor_smart_monitoring/
├── api/                  # Rotas da API
│   ├── cameras.py        # Endpoints de gerenciamento de câmeras
│   ├── events.py         # Endpoints de gerenciamento de eventos
│   ├── users.py          # Endpoints de gerenciamento de usuários
│   └── onvif.py          # Endpoints de controle ONVIF
├── core/                 # Lógica principal
│   ├── camera.py         # Gerenciamento de câmeras
│   ├── detection.py      # Detecção de objetos com YOLOv8
│   ├── onvif.py          # Controle ONVIF para câmeras PTZ
│   └── recording.py      # Gravação de vídeo e gerenciamento de eventos
├── websocket/            # WebSocket para notificações
│   ├── manager.py        # Gerenciador de conexões WebSocket
│   └── endpoints.py      # Endpoints WebSocket
├── auth/                 # Autenticação e autorização
│   └── auth.py           # Lógica de autenticação JWT
├── models/               # Modelos do banco de dados
│   └── models.py         # Modelos SQLAlchemy
├── db/                   # Configuração do banco de dados
│   └── base.py           # Configuração do SQLAlchemy
├── alembic/              # Migrações do banco de dados
├── tests/                # Testes automatizados
├── main.py               # Ponto de entrada da aplicação
├── requirements.txt      # Dependências Python
├── Dockerfile            # Configuração do Docker
└── docker-compose.yml    # Configuração do Docker Compose
```

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e enviar pull requests.

## 📞 Contato

Para mais informações, entre em contato com a equipe de desenvolvimento.

## 📝 API Endpoints

### Autenticação
- `POST /auth/login` - Autenticação de usuários
- `POST /auth/register` - Registro de novos usuários
- `GET /auth/me` - Informações do usuário atual

### Câmeras
- `GET /cameras` - Lista todas as câmeras
- `POST /cameras` - Adiciona uma nova câmera
- `GET /cameras/{id}` - Detalhes de uma câmera
- `PUT /cameras/{id}` - Atualiza uma câmera
- `DELETE /cameras/{id}` - Remove uma câmera
- `POST /cameras/{id}/start` - Inicia o streaming de uma câmera
- `POST /cameras/{id}/stop` - Para o streaming de uma câmera
- `GET /cameras/{id}/stats` - Estatísticas de uma câmera

### Controle ONVIF
- `POST /onvif/cameras/{id}/ptz` - Controla movimentos PTZ
- `GET /onvif/cameras/{id}/presets` - Lista presets de uma câmera
- `POST /onvif/cameras/{id}/presets` - Cria um novo preset
- `POST /onvif/cameras/{id}/presets/{preset_id}/goto` - Move para um preset
- `DELETE /onvif/cameras/{id}/presets/{preset_id}` - Remove um preset
- `GET /onvif/cameras/{id}/info` - Informações do dispositivo
- `GET /onvif/cameras/{id}/capabilities` - Capacidades ONVIF
- `POST /onvif/discover` - Descobre dispositivos ONVIF na rede

### Eventos
- `GET /events` - Lista todos os eventos
- `GET /events/{id}` - Detalhes de um evento
- `POST /events` - Cria um novo evento manualmente
- `DELETE /events/{id}` - Remove um evento
- `GET /events/{id}/video` - Obtém o vídeo de um evento
- `GET /events/{id}/image` - Obtém a imagem de um evento
- `GET /events/stats` - Estatísticas de eventos

### Usuários
- `GET /users` - Lista todos os usuários (admin)
- `POST /users` - Cria um novo usuário (admin)
- `GET /users/{id}` - Detalhes de um usuário
- `PUT /users/{id}` - Atualiza um usuário
- `DELETE /users/{id}` - Remove um usuário (admin)

### WebSockets
- `WS /ws/events` - Notificações de eventos em tempo real
- `WS /ws/cameras/{id}` - Streaming de vídeo em tempo real
