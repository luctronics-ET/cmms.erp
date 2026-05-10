# 🎥 Sistema de Vigilância Integrado com IA

Sistema web para gerenciar múltiplas câmeras IP (PTZ + Térmica) com detecção inteligente de pessoas, fogo e objetos aéreos em tempo real.

---

## 📋 Requisitos

- **Python 3.11+**
- **Node.js 18+** (para frontend)
- **Docker + Docker Compose** (opcional, recomendado)
- **Câmeras Hikvision IP** com RTSP habilitado
- **Processador**: Mínimo CPU 4 cores, 8GB RAM (para processamento de IA)

---

## 🚀 Instalação Rápida (com Docker)

```bash
# 1. Clone o repositório
git clone <seu-repo>
cd vigilancia-integrada

# 2. Configure as câmeras em app.py (CAMERAS_CONFIG)
nano app.py

# 3. Inicie os serviços
docker-compose up -d

# 4. Acesse a interface
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# PgAdmin: http://localhost:5050 (admin/admin123)
```

---

## ⚙️ Configuração de Câmeras

Edite `CAMERAS_CONFIG` em `app.py` com as informações de suas câmeras:

```python
CAMERAS_CONFIG = {
    "dome_1": {
        "ip": "192.168.0.198",
        "username": "admin",
        "password": "971001",
        "name": "Dome PTZ - Entrada",
        "type": "ptz",  # ou "fixed"
        "thermal": False,  # ou True
        "rtsp_port": 554,
        "position": {"x": 450, "y": 300},  # Posição no mapa (pixels)
        "fov": {
            "horizontal": 70,  # Ângulo horizontal (graus)
            "vertical": 50
        }
    },
    # Adicione mais câmeras aqui...
}
```

### Descobrir streams RTSP da sua câmera Hikvision

```bash
# Teste a URL RTSP:
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate \
  -of default=noprint_wrappers=1:nokey=1:nokey=1 \
  rtsp://admin:971001@192.168.0.198:554/stream0
```

---

## 📊 Detecções Suportadas

### **Câmeras Térmicas**

| Detecção | Tipo | Threshold | Uso |
|----------|------|-----------|-----|
| **Pessoas** | Humanóide quente | T > 35-40°C | Monitoramento de vegetação, áreas abertas |
| **Fogo** | Região muito quente | T > 60°C | Detecção de incêndios em tempo real |
| **Barcos** | Grandes contornos quentes | Área > 500px | Monitoramento de costa/rio |
| **Pessoas em água** | Pontos quentes flutuando | Área 100-500px | Resgate em água |
| **Balões/Objetos aéreos** | Pequenos contornos claros | Céu, 50-5000px | Detecção de invasão aérea |
| **Movimento** | Frame diff > threshold | >5% diff | Ativação de câmeras |

### **Câmeras Visíveis**

- Movimento geral via frame diff
- Possibilidade de integração YOLO v8 para detecção de pessoas (futura)

---

## 🗺️ Configurar Mapa (Imagem de Fundo)

1. **Adicione uma imagem do mapa** em `public/map.png` (800x600 ou maior)
2. **Configure posições das câmeras** no `CAMERAS_CONFIG`
   - `x`, `y`: coordenadas em pixels na imagem
   - `fov`: ângulo de visão (horizontal/vertical)

### Exemplo de posicionamento:

```
   x=0 (esquerda)                    x=800 (direita)
   ┌─────────────────────────────────────────────┐
   │  🎥 Entrada (450, 300)                      │
y=0│                                              │
   │      🌡️ Perímetro (600, 250)                │
   │                                              │
   │  📹 Vegetação (300, 400)                    │
   │                                              │
   │ 🌡️ Costa (200, 150)                        │
y=600└─────────────────────────────────────────────┘
```

---

## 🔌 Arquitetura da API

### **Endpoints Principais**

```bash
# Obter lista de câmeras
GET /api/cameras

# Snapshot de uma câmera (JPEG)
GET /api/cameras/{camera_id}/snapshot

# Obter detecções recentes
GET /api/detections/{camera_id}?limit=50

# Enviar comando PTZ
POST /api/ptz/{camera_id}/command
Content-Type: application/json
{
  "pan": 1,      # -1=esquerda, 0=parado, 1=direita
  "tilt": -1,    # -1=cima, 0=parado, 1=baixo
  "zoom": 0,     # -1=out, 0=parado, 1=in
  "speed": 5     # 1-7
}

# Health check
GET /health
```

### **WebSocket para Eventos em Tempo Real**

```javascript
// Conectar
const ws = new WebSocket('ws://localhost:8000/ws/events');

// Receber eventos
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'detection') {
    console.log('Detecção:', msg.data);
  }
};
```

---

## 🔧 Calibração de Detecções

Os thresholds estão em `DETECTION_THRESHOLDS`:

```python
DETECTION_THRESHOLDS = {
    "thermal_person": 37,       # Temperatura mínima (corpo humano)
    "thermal_fire": 60,         # Temperatura de fogo
    "thermal_difference": 10,   # Diferença T° para contraste
    "movement_threshold": 5,    # % de diferença entre frames
}
```

### Como calibrar para sua câmera térmica:

1. **Capture um snapshot** de cada câmera
2. **Ajuste thresholds** incrementalmente
3. **Teste com objetos reais** (pessoa, fogo de teste, barco)
4. **Valide taxa de falsos positivos**

```python
# Script de teste
import cv2
from app import thermal_detector

frame = cv2.imread('thermal_sample.jpg')
detections = thermal_detector.detect_hot_regions(frame, min_temp=37)
print(f"Detectadas {len(detections)} regiões quentes")
```

---

## 🚨 Alertas e Notificações

### Estrutura de Eventos (WebSocket)

```json
{
  "type": "detection",
  "data": {
    "camera_id": "thermal_1",
    "camera_name": "Térmica Bullet - Vegetação",
    "timestamp": "2024-01-15T14:32:45.123Z",
    "detections": [
      {
        "type": "person",
        "bbox": {"x": 120, "y": 340, "w": 45, "h": 80},
        "area": 3600,
        "confidence": 85
      },
      {
        "type": "movement",
        "movement_percent": 12.5
      }
    ]
  }
}
```

### Filtros de Alerta (futura implementação)

```python
# Exemplo: Alertar apenas sobre fogo ou pessoas em áreas sensíveis
if detection['type'] in ['fire_or_vehicle', 'person']:
    if camera_id in ['thermal_sky', 'thermal_coast']:
        send_alert_webhook(detection)
```

---

## 📈 Processamento de IA (Extensão Futura)

### Adicionar YOLO v8 para câmeras visíveis:

```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # Nano (mais rápido)

def detect_persons_yolo(frame):
    results = model(frame, verbose=False)
    for detection in results[0].boxes:
        if detection.cls == 0:  # Classe "person"
            x1, y1, x2, y2 = detection.xyxy[0]
            confidence = detection.conf[0]
            yield {
                'type': 'person_yolo',
                'bbox': {'x': x1, 'y': y1, 'w': x2-x1, 'h': y2-y1},
                'confidence': confidence
            }
```

---

## 📝 Logging e Debug

### Ativar verbose logging:

```bash
# Docker
docker logs -f vigilancia-backend

# Local
LOG_LEVEL=debug python app.py

# Visualizar frames com detecções (desenvolvimento)
SAVE_DEBUG_FRAMES=true python app.py
# Frames salvos em ./debug_frames/
```

---

## 🔐 Segurança

⚠️ **IMPORTANTE**: Este sistema está em rede local. Para usar na internet:

1. **Use HTTPS/WSS** (reverse proxy com nginx/Caddy)
2. **Autenticação JWT** nos endpoints
3. **Rate limiting** nas APIs
4. **Isoler câmeras** em VLAN separada

### Exemplo com nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name vigilancia.seu-dominio.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_buffering off;
    }

    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

---

## 🐛 Troubleshooting

### Câmera offline

```bash
# Testar conectividade
ping 192.168.0.198

# Testar RTSP
ffprobe rtsp://admin:971001@192.168.0.198:554/stream0

# Verificar logs
docker logs vigilancia-backend | grep "192.168.0.198"
```

### Alto uso de CPU

- Reduzir FPS (aumentar intervalo entre frames)
- Aumentar tamanho mínimo de detecção (filtra ruído)
- Usar `opencv-python-headless` em vez de versão GUI

### WebSocket lento

- Aumentar workers em `uvicorn` (docker-compose)
- Usar Redis para cache de eventos
- Implementar rate limiting de eventos

---

## 📚 Referências

- [ONVIF Spec](https://www.onvif.org/)
- [Hikvision RTSP URLs](https://www.hikvision.com/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [FastAPI](https://fastapi.tiangolo.com/)

---

## 📄 Licença

MIT License - Veja LICENSE.txt

---

## 📞 Suporte

Para issues, sugestões ou contribuições, abra uma issue no repositório.

**Última atualização**: Janeiro 2024
