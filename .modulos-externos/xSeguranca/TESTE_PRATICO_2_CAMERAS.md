# 🎬 Guia de Teste Prático - Suas 2 Câmeras PTZ

## ⏱️ Tempo estimado: 10-15 minutos

---

## Passo 1: Preparar Ambiente (2 min)

### 1.1 Instalar dependências mínimas

```bash
# Se não tiver Python 3.11+
python --version

# Instalar opencv (leve, sem GPU)
pip install opencv-python

# Verificar instalação
python -c "import cv2; print(f'OpenCV {cv2.__version__} OK')"
```

### 1.2 Fazer download do script

```bash
# Se ainda não tiver baixado:
# Arquivo: test_suas_cameras.py (neste repositório)

# Ou criar manualmente (copiar conteúdo abaixo)
# ... ver arquivo test_suas_cameras.py
```

---

## Passo 2: Validar Conectividade (3 min)

### 2.1 Ping às câmeras

```bash
# Terminal 1: Teste de rede
ping 192.168.0.198    # Deve responder
ping 192.168.0.199    # Deve responder

# Resultado esperado:
# PING 192.168.0.198 (192.168.0.198): 56 data bytes
# 64 bytes from 192.168.0.198: icmp_seq=0 ttl=64 time=2.345 ms
```

### 2.2 Acessar via web browser (validar credenciais)

```
Abrir no navegador:
- http://192.168.0.198/main.htm
- http://192.168.0.199/main.htm

Login: admin / 971001

Se não abrir:
  → IP errado
  → Câmera desligada
  → Firewall bloqueando
```

---

## Passo 3: Rodar Script de Teste (5 min)

### 3.1 Executar

```bash
python test_suas_cameras.py
```

### 3.2 Resultado esperado

```
============================================================
🎬 TESTE DE CÂMERAS PTZ HIKVISION
============================================================

============================================================
🎥 Testando: Dome 1 - Entrada
============================================================
📡 URL: rtsp://admin:971001@192.168.0.198:554/stream0

1️⃣  Conectando ao stream RTSP... ✅ Conectado

2️⃣  Obtendo propriedades do stream:
   • Resolução: 1920x1080
   • FPS: 25

3️⃣  Capturando e analisando 30 frames... ✅
   • Taxa de sucesso: 100.0% (30/30 frames)
   • FPS real (medido): 29.8

4️⃣  Salvando snapshot... ✅ snapshots/dome_1_latest.jpg

5️⃣  Câmera RGB (não térmica)
   • Média de brilho: 128.5
   • Variação: 45.2
   ✅ Qualidade aparenta OK

✅ TESTE PASSOU: Dome 1 - Entrada

============================================================
🎥 Testando: Dome 2 - Perímetro (Térmica)
============================================================
[... similar output ...]

5️⃣  Analisando imagem térmica...
   • Média de intensidade: 120.3
   • Desvio padrão: 35.7
   • Min-Max: 10-240
   • Pixels quentes (>150): 8.5%
   ✅ Distribuição térmica aparenta OK

✅ TESTE PASSOU: Dome 2 - Perímetro (Térmica)

============================================================
📊 RELATÓRIO FINAL
============================================================
✅ PASSOU Dome 1 - Entrada
✅ PASSOU Dome 2 - Perímetro (Térmica)

Resultado: 2/2 câmeras passaram ✅

🎉 Tudo OK! Próximo passo: rodar docker-compose up -d

📂 Snapshots salvos em: ./snapshots/
============================================================
```

---

## Passo 4: Verificar Snapshots (2 min)

```bash
# Ver imagens capturadas
ls -lh snapshots/

# Abrir em visualizador
# Windows: start snapshots\dome_1_latest.jpg
# macOS:   open snapshots/dome_1_latest.jpg
# Linux:   eog snapshots/dome_1_latest.jpg
```

**Se as imagens aparecerem:**
- ✅ Conexão RTSP está funcionando
- ✅ Câmeras estão online
- ✅ Credenciais corretas

---

## Passo 5: (Opcional) Testar RTSP Diretamente (3 min)

Se quiser validar antes de rodar o Docker:

```bash
# Instalar ffmpeg (se não tiver)
# Windows: choco install ffmpeg
# macOS:   brew install ffmpeg
# Linux:   sudo apt-get install ffmpeg

# Testar stream com ffplay
ffplay rtsp://admin:971001@192.168.0.198:554/stream0

# Ou com ffprobe (sem GUI)
ffprobe -v error -select_streams v:0 -show_entries \
  stream=width,height,avg_frame_rate -of \
  default=noprint_wrappers=1:nokey=1:nokey=1 \
  rtsp://admin:971001@192.168.0.198:554/stream0

# Resultado esperado:
# 1920
# 1080
# 25/1
```

---

## Passo 6: Se Algo Falhar

### ❌ "Connection refused" ou timeout

```bash
# 1. Verificar IP
ping 192.168.0.198
# Se não responder → IP errado ou câmera desligada

# 2. Verificar porta RTSP
nmap -p 554 192.168.0.198
# Se fechada → RTSP desabilitado na câmera

# 3. Verificar credenciais
# Acessar http://192.168.0.198/main.htm
# Se pedir senha → credenciais erradas
```

### ❌ "Failed to open codec"

```bash
# Problema com codec (H.264, H.265, MJPEG)
# Solução: Verificar stream secondary da câmera

# Tentar stream1 em vez de stream0:
ffplay rtsp://admin:971001@192.168.0.198:554/stream1

# Ou stream2:
ffplay rtsp://admin:971001@192.168.0.198:554/stream2
```

### ❌ "OpenCV not found"

```bash
# Reinstalar opencv
pip install --force-reinstall opencv-python

# Ou usar versão headless (sem GUI)
pip install opencv-python-headless
```

---

## Passo 7: Próximas Ações (Após sucesso ✅)

### A. Se quer testar full stack (Docker):

```bash
# 1. Editar app.py com seus IPs (já preenchido acima)
#    Linha ~50: CAMERAS_CONFIG

# 2. Iniciar Docker
docker-compose up -d

# 3. Aguardar 30 segundos e abrir
http://localhost:3000

# 4. Tirar print do mapa com câmeras online 🎉
```

### B. Se quer rodar local (sem Docker):

```bash
# 1. Instalar dependências backend
pip install -r requirements.txt

# 2. Instalar dependências frontend
npm install

# 3. Terminal 1: Backend
python app.py
# Esperado: Uvicorn running on http://0.0.0.0:8000

# 4. Terminal 2: Frontend
npm start
# Esperado: http://localhost:3000 abre no navegador

# 5. Usar normalmente!
```

---

## Troubleshooting Rápido

| Erro | Causa | Solução |
|------|-------|---------|
| `rtsp://... connection refused` | Câmera offline | `ping 192.168.0.198` |
| `401 Unauthorized` | Senha errada | Verificar em http://192.168.0.198/main.htm |
| `Operation timed out` | RTSP desabilitado | Abilitar em configurações da câmera |
| `Frame size 0x0` | Stream corrompido | Tentar `/stream1` em vez de `/stream0` |
| `High CPU usage` | OpenCV processando muito | Normal, reduz com mais FPS configurado |

---

## Checklist Final

- [ ] Ping para ambas câmeras responde
- [ ] `test_suas_cameras.py` retorna 2/2 ✅
- [ ] Snapshots aparecem em `./snapshots/`
- [ ] Dome 1 (RGB) aparece com brilho normal
- [ ] Dome 2 (Térmica) aparece com cores diferentes
- [ ] FPS real está próximo do esperado (~25-30)

---

## Próximos Passos

**Depois que validar que está tudo OK:**

1. **Calibrar thresholds térmicos**
   - Editar `DETECTION_THRESHOLDS` em app.py
   - Testar com pessoa real perto de cada câmera

2. **Configurar mapa**
   - Adicionar imagem em `public/map.png`
   - Ajustar posições em `CAMERAS_CONFIG`

3. **Rodar sistema completo**
   - `docker-compose up -d` e usar em http://localhost:3000

---

## Dúvidas?

Mensagens de erro específicas que você receber:
- Copie o erro exato
- Rode `python test_suas_cameras.py 2>&1 | tee debug.log`
- Análise o arquivo `debug.log`

---

**Boa sorte! Qualquer dúvida durante o teste, avise.** 🎬

Última atualização: Janeiro 2024
