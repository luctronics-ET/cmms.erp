# 🚀 Setup Rápido - Sistema de Vigilância Integrado

## Checklist de Inicialização (30 min)

### Passo 1: Clonar e configurar
```bash
git clone <seu-repo> vigilancia
cd vigilancia

# Copiar configuração de exemplo
cp CAMERAS_CONFIG.example.py app.py  # Ou editar manualmente

# IMPORTANTE: Editar IPs das câmeras em app.py (CAMERAS_CONFIG)
nano app.py
```

### Passo 2: Testar câmeras (antes de rodar full stack)
```bash
# Instalar dependências mínimas
pip install opencv-python requests

# Rodar script de validação
python test_cameras.py --all

# Resultado esperado:
# ✓ dome_1: OK
# ✓ dome_2: OK
# ✓ thermal_1: OK
# ...

# Se alguma falhar, corrigir IP/senha/conectividade primeiro
```

### Passo 3: Docker Compose (recomendado)
```bash
# Instalar Docker + Docker Compose (se não tiver)
# macOS: https://www.docker.com/products/docker-desktop
# Linux: curl -fsSL https://get.docker.com | sh

# Iniciar stack completa
docker-compose up -d

# Verificar status
docker-compose ps

# Ver logs do backend
docker logs -f vigilancia-backend

# Resultado esperado em ~30s:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Iniciando sistema de vigilância...
# ✓ Sistema iniciado com 5 câmeras
```

### Passo 4: Acessar interfaces
- **Frontend React:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Docs Swagger:** http://localhost:8000/docs
- **PgAdmin:** http://localhost:5050 (admin/admin123)

---

## Instalação Local (Sem Docker)

### Requisitos
```bash
Python 3.11+
Node.js 18+
PostgreSQL 16+ (ou usar container: docker run -d postgres:16)
Redis 7+ (ou usar container: docker run -d redis:7)
```

### Backend
```bash
# 1. Criar venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou: venv\Scripts\activate  # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar servidor
python app.py
# Esperado: Uvicorn running on http://0.0.0.0:8000
```

### Frontend
```bash
# 1. Criar projeto React (se não existir)
npx create-react-app frontend
cd frontend

# 2. Copiar arquivos
cp ../App.tsx src/
cp ../App.css src/

# 3. Instalar dependências
npm install

# 4. Rodar dev server
npm start
# Esperado: http://localhost:3000 abre no navegador
```

---

## Primeira Execução

### 1. Validar saúde do sistema
```bash
curl http://localhost:8000/health

# Resposta esperada:
{
  "status": "ok",
  "online_cameras": 5,
  "total_cameras": 5,
  "timestamp": "2024-01-15T14:30:00.123456"
}
```

### 2. Listar câmeras
```bash
curl http://localhost:8000/api/cameras

# Resposta esperada:
{
  "cameras": [
    {
      "id": "dome_1",
      "name": "Dome PTZ - Entrada",
      "type": "ptz",
      "thermal": false,
      "position": {"x": 450, "y": 300},
      "fov": {"horizontal": 70, "vertical": 50},
      "status": "online"
    },
    ...
  ]
}
```

### 3. Capturar snapshot
```bash
curl -o snapshot.jpg http://localhost:8000/api/cameras/dome_1/snapshot
# Arquivo .jpg deve aparecer com imagem da câmera
```

### 4. Testar WebSocket (events)
```bash
# Terminal 1: Backend rodando

# Terminal 2: Cliente WebSocket
python3 -c "
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f'Evento recebido: {data[\"type\"]}')
    if data['type'] == 'detection':
        print(f'  Camera: {data[\"data\"][\"camera_name\"]}')
        print(f'  Detecções: {data[\"data\"][\"detections\"]}')

ws = websocket.WebSocketApp('ws://localhost:8000/ws/events', on_message=on_message)
ws.run_forever()
"
# Esperar 30s. Se houver movimento em alguma câmera, verá evento aqui
```

### 5. Acessar frontend
Abrir http://localhost:3000 no navegador.

---

## Calibração de Câmeras Térmicas

### Objetivo: Ajustar thresholds para sua localização

**Arquivo:** `app.py` → `DETECTION_THRESHOLDS`

```python
DETECTION_THRESHOLDS = {
    "thermal_person": 37,       # ← Ajustar aqui
    "thermal_fire": 60,         # ← E aqui
    "thermal_difference": 10,
    "movement_threshold": 5,
}
```

### Procedimento (15 min por câmera)

1. **Capturar baseline** (sem atividades):
   ```bash
   curl -o thermal_1_idle.jpg http://localhost:8000/api/cameras/thermal_1/snapshot
   ```

2. **Capturar com atividade** (pessoa perto, etc):
   ```bash
   # Posicionar pessoa na frente da câmera
   curl -o thermal_1_person.jpg http://localhost:8000/api/cameras/thermal_1/snapshot
   ```

3. **Analisar** (python):
   ```python
   import cv2
   from app import thermal_detector
   
   frame = cv2.imread('thermal_1_person.jpg')
   detections = thermal_detector.detect_hot_regions(frame)
   
   print(f"Detectadas {len(detections)} regiões")
   for det in detections:
       print(f"  {det['type']}: {det}")
   ```

4. **Ajustar threshold se necessário**:
   - Muitos falsos positivos? Aumentar `thermal_person` (ex: 37 → 40)
   - Não detecta pessoas? Reduzir `thermal_person` (ex: 37 → 35)
   - Similar para `thermal_fire` com cenários de fogo

### Validação

```bash
# Depois de calibrar, testar detecção em tempo real
# Observar timeline de eventos na web UI

# Se vindo muitos eventos falsos:
#   → Aumentar thresholds
# Se não está detectando:
#   → Reduzir thresholds
# Se está detectando barcos/pessoas como fogo:
#   → Verificar FOV e contexto da câmera
```

---

## Troubleshooting Rápido

### ❌ Câmera não conecta

```bash
# 1. Verificar IP
ping 192.168.0.198

# 2. Testar RTSP
ffprobe rtsp://admin:971001@192.168.0.198:554/stream0

# 3. Ver logs
docker logs vigilancia-backend | grep "192.168.0.198"

# 4. Verificar credenciais (acesso via web)
# Abrir http://192.168.0.198/main.htm no navegador
```

### ❌ Backend não inicia

```bash
# Ver erro completo
docker logs vigilancia-backend

# Erros comuns:
# "Address already in use" → porta 8000 ocupada
#   → docker-compose down && docker-compose up

# "OpenCV not found" → reinstalar dependência
#   → pip install --force-reinstall opencv-python-headless

# "Connection refused" → PostgreSQL/Redis offline
#   → Verificar docker-compose.yml
```

### ❌ WebSocket não funciona

```bash
# Verificar se conecta
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8000/ws/events

# Se retornar 426 ou erro: backend pode não estar pronto
# Aguardar ~10s e tentar novamente
```

### ❌ Frontend não carrega

```bash
# Verificar se React está rodando
curl http://localhost:3000

# Ver logs do React
docker logs vigilancia-frontend-dev

# Erros comuns:
# CORS error → Verificar CORS em app.py (deve estar * para dev)
# API_URL errado → Verificar env vars no docker-compose
```

---

## Próximos Passos Recomendados

### Curto Prazo (Semana 1)
- [ ] Calibrar todas as câmeras térmicas
- [ ] Testar detecção com objetos reais (pessoa, fogo teste)
- [ ] Configurar mapa (imagem `public/map.png`)
- [ ] Marcar posições das câmeras no mapa

### Médio Prazo (Semana 2-3)
- [ ] Integrar ONVIF para controle PTZ
- [ ] Implementar filtros de alerta (não alertar em cada frame)
- [ ] Adicionar autenticação JWT
- [ ] Configurar HTTPS com reverse proxy

### Longo Prazo (Mês 2+)
- [ ] Integrar YOLO v8 para IA avançada
- [ ] Conectar Home Assistant
- [ ] Implementar recorder para histórico
- [ ] Adicionar notificações (Discord, Telegram)

---

## Contato & Docs

- **Docs FastAPI:** http://localhost:8000/docs
- **Repo:** seu-repo-aqui
- **Issues:** Abrir no GitHub

---

**Última atualização:** Janeiro 2024
**Versão:** 1.0.0-beta
