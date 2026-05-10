# 📖 Amanhã: Adicionar as 3 Câmeras Térmicas

## ⏱️ Tempo estimado: 5 minutos (sem parar o sistema)

---

## Contexto

**Hoje:** Sistema rodando com 2 câmeras RGB (Dome PTZ)
**Amanhã:** Adicionar 3 câmeras térmicas Hikvision

**Estrutura:** Tudo já está preparado. Você só precisa descomentar as linhas em `app.py`.

---

## Passo 1: Descobrir os IPs das 3 Térmicas (5 min)

As 3 câmeras térmicas chegam amanhã. Antes de conectá-las:

### 1.1 Conectar ao mesmo switch/rede que as PTZ

```
Rede local:
├── WiFi: seu notebook
├── Switch de rede:
│   ├── 192.168.0.198 (Dome 1 - RGB)
│   ├── 192.168.0.199 (Dome 2 - RGB)
│   ├── 192.168.0.201 (Térmica 1) ← conectar aqui
│   ├── 192.168.0.202 (Térmica 2) ← conectar aqui
│   └── 192.168.0.203 (Térmica 3) ← conectar aqui
```

### 1.2 Descubrir IPs automáticos (se não tiverem IPs fixos)

```bash
# Linux/macOS: nmap
brew install nmap  # macOS
sudo apt-get install nmap  # Linux

# Escanear rede
nmap -sn 192.168.0.1/24

# Resultado esperado:
# Nmap scan report for 192.168.0.198
# Host is up (0.0032s latency).
# Nmap scan report for 192.168.0.199
# Host is up (0.0015s latency).
# Nmap scan report for 192.168.0.201  ← Térmicas
# Host is up (0.0018s latency).
# ...
```

### 1.3 Acessar cada uma via web

```
http://192.168.0.201/main.htm
http://192.168.0.202/main.htm
http://192.168.0.203/main.htm

Login: admin / 971001 (mesma senha das PTZ)
```

---

## Passo 2: Editar app.py (2 min)

### 2.1 Abrir app.py

```bash
nano app.py
# ou abrir em editor (VS Code, Sublime, etc)
```

### 2.2 Encontrar as linhas comentadas (linha ~50)

```python
# Procurar por:
# "thermal_1": {
# "thermal_2": {
# "thermal_3": {
```

### 2.3 Descomentar e preencher IPs reais

```python
# ❌ ANTES (comentado):
# "thermal_1": {
#     "ip": "192.168.0.201",
#     "username": "admin",
#     "password": "971001",
#     ...
# },

# ✅ DEPOIS (descomentado e com IPs reais):
"thermal_1": {
    "ip": "192.168.0.201",  # ← Seu IP real
    "username": "admin",
    "password": "971001",
    "name": "Térmica Bullet - Vegetação",
    "type": "fixed",
    "thermal": True,
    "rtsp_port": 554,
    "position": {"x": 300, "y": 450},  # ← Ajustar posição depois
    "fov": {"horizontal": 50, "vertical": 40}
},
"thermal_2": {
    "ip": "192.168.0.202",  # ← Seu IP real
    ...
},
"thermal_3": {
    "ip": "192.168.0.203",  # ← Seu IP real
    ...
},
```

### 2.4 Salvar arquivo

```
Ctrl+S (ou Cmd+S no macOS)
```

---

## Passo 3: Recarregar Backend (1 min, sem parar containers)

### Opção A: Reiniciar apenas o backend (recomendado)

```bash
# Parar só o backend
docker-compose restart vigilancia-backend

# Aguardar ~5s
# Logs vão mostrar: ✓ Sistema iniciado com 5 câmeras

# Verificar
curl http://localhost:8000/api/cameras | python -m json.tool
```

### Opção B: Reiniciar tudo (se opção A não funcionar)

```bash
# Parar e reiniciar stack completa
docker-compose down
docker-compose up -d

# Aguardar ~30s
# Abrir http://localhost:3000 novamente
```

---

## Passo 4: Validar no Browser (1 min)

### 4.1 Recarregar a página

```
http://localhost:3000
F5 ou Cmd+R
```

### 4.2 Verificar se 5 câmeras aparecem

**Status bar deve mostrar:** `🟢 5/5 câmeras online`

Ícones no mapa:
- 🎥 🎥 (2 Domes RGB)
- 🌡️ 🌡️ 🌡️ (3 Térmicas)

### 4.3 Se alguma aparecer offline 🔴

```bash
# Debugar
docker logs vigilancia-backend | grep "thermal_1"

# Provável causa: IP errado
# Solução: Verificar IP real, editar app.py novamente, reiniciar
```

---

## Passo 5: Ajustar Posições no Mapa (5 min)

Agora você tem 5 câmeras. Ajustar posições para seu ambiente:

### 5.1 Editar posições em app.py

```python
"position": {"x": 300, "y": 450},  # x, y em pixels do mapa
```

### 5.2 Dimensões do mapa

```
Mapa padrão: 800x600 pixels

x=0 (esquerda) → x=800 (direita)
y=0 (topo) → y=600 (fundo)

Exemplo:
├── x=100, y=100 (canto superior esquerdo)
├── x=400, y=300 (centro)
└── x=700, y=500 (canto inferior direito)
```

### 5.3 Testar no browser

```
F5 para recarregar
Ícones devem se mover para novas posições
```

---

## Passo 6: Testar Detecção Térmica (5 min)

### 6.1 Colocar pessoa perto da térmica

Posicione alguém próximo a uma das câmeras térmicas.

### 6.2 Observar timeline

A timeline na web UI deve mostrar:
- 👤 `person` (pessoa detectada)
- ⚡ `movement` (movimento)

### 6.3 Calibrar se necessário

Se não detecta:
```python
# Em app.py, reduzir threshold
"thermal_person": 35,  # Era 37, agora 35 (mais sensível)
```

Se detecta muito (falsos positivos):
```python
"thermal_person": 40,  # Era 37, agora 40 (menos sensível)
```

Depois: `docker-compose restart vigilancia-backend`

---

## Checklist Amanhã

- [ ] Conectar 3 câmeras térmicas à rede
- [ ] Descobrir IPs (ping/nmap)
- [ ] Editar app.py com IPs reais
- [ ] `docker-compose restart vigilancia-backend`
- [ ] Recarregar browser (F5)
- [ ] Verificar 5/5 câmeras online 🟢
- [ ] Ajustar posições no mapa
- [ ] Testar detecção com pessoa real
- [ ] Calibrar thresholds se necessário

---

## Se Algo Quebrar Amanhã

### ❌ "5/5 câmeras online, mas algumas 🔴"

```bash
# Debug
docker logs vigilancia-backend | grep "thermal"

# Likely issues:
# 1. IP errado → editar app.py
# 2. Câmera desligada → ligar
# 3. RTSP desabilitado → habilitar em configurações
# 4. Firewall → permitir porta 554

# Fix: editar app.py + docker-compose restart vigilancia-backend
```

### ❌ "Backend crash após editar"

```bash
# Ver erro
docker logs vigilancia-backend -f

# Likely issues:
# 1. Syntax erro em JSON (virgula faltante)
# 2. IP inválido

# Fix: copiar linha inteira de camera comentada, colar, editar só IP
```

### ❌ "Detecção não funciona"

```bash
# Likely issues:
# 1. Térmicas precisam de calibração de temperatura
# 2. Thresholds errados para sua localização
# 3. FOV muito pequeno

# Fix: reduzir threshold (37→35) ou aumentar FOV
```

---

## Estrutura Pronta Para Crescimento

Seu sistema está estruturado para:

```
Hoje:  2 câmeras RGB
↓
Amanhã: + 3 térmicas (total 5)
↓
Semana que vem: + ESP32 sensores (MQTT futura)
↓
Mês que vem: + YOLO v8 (IA avançada)
```

Tudo sem refatoração. Só editar `CAMERAS_CONFIG`.

---

## Comando Rápido Amanhã

```bash
# 1. Editar app.py (descomentar + IPs)
# 2. Executar:
docker-compose restart vigilancia-backend

# 3. Aguardar 5s
# 4. Abrir http://localhost:3000
# 5. Verificar: 5/5 online ✅
```

**Pronto em 5 minutos.**

---

**Amanhã você tem tudo preparado. Só não esqueça os IPs das térmicas!** 🎬
