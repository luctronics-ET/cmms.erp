# 📚 ÍNDICE COMPLETO - Sistema de Vigilância Integrado

## 🎯 Seu Situação Agora

✅ **Hoje:** 2 câmeras RGB (Dome PTZ em casa)
✅ **Amanhã:** + 3 câmeras térmicas
✅ **Sistema:** Docker completo, pronto para rodar

---

## 📂 ARQUIVOS - Ordem de Uso

### 🚀 INICIAR HOJE (1️⃣ Faça isto primeiro)

| Arquivo | O que faz | Quando usar | Tempo |
|---------|-----------|------------|-------|
| **COMECE_HOJE.md** | 📖 Guia super rápido | Leia agora | 2 min |
| **start.sh** (Linux/Mac) | 🎬 Inicia tudo automaticamente | Após ler guia | 30 seg |
| **start.bat** (Windows) | 🎬 Inicia tudo automaticamente | Após ler guia | 30 seg |

### 📊 VALIDAR HOJE (2️⃣ Depois que iniciou)

| Arquivo | O que faz | Quando usar | Resultado |
|---------|-----------|------------|-----------|
| **TESTE_PRATICO_2_CAMERAS.md** | 📖 Troubleshooting detalhado | Se algo falhar | Corrige problema |
| **test_suas_cameras.py** | 🧪 Testa câmeras sem Docker | Opcional (debug) | 2/2 ✅ |

### 🔧 CONFIGURAÇÃO (3️⃣ Para amanhã)

| Arquivo | O que faz | Quando usar |
|---------|-----------|------------|
| **AMANHA_ADICIONAR_TERMICAS.md** | 📖 Guia amanhã | Quando chegar as térmicas |
| **SUAS_CAMERAS_CONFIG.txt** | 📝 Config pronta para suas cams | Referência |

### 💻 CÓDIGO (4️⃣ Você não edita, só para referência)

| Arquivo | Função |
|---------|--------|
| **app.py** | Backend FastAPI com detecção |
| **App.tsx** | Frontend React (componentes) |
| **App.css** | Estilos da UI |
| **docker-compose.yml** | Orquestração Docker |
| **Dockerfile.backend** | Container do backend |
| **package.json** | Dependências npm |
| **requirements.txt** | Dependências Python |

### 📚 DOCUMENTAÇÃO (5️⃣ Leia quando quiser aprofundar)

| Arquivo | Propósito |
|---------|-----------|
| **README.md** | Documentação completa |
| **RESUMO_EXECUTIVO.md** | Visão 30.000 pés |
| **SETUP_RÁPIDO.md** | Setup local (sem Docker) |

---

## 🎬 ROTEIROS POR CENÁRIO

### Cenário 1: "Quero testar AGORA com Docker"

```
1. Ler: COMECE_HOJE.md (2 min)
2. Rodar: ./start.sh (ou start.bat no Windows)
3. Aguardar 30s
4. Abrir: http://localhost:3000
5. Ver: 🟢 2/2 câmeras online
✅ Pronto!
```

### Cenário 2: "Algo não funciona"

```
1. Terminal:
   docker-compose ps
   docker logs vigilancia-backend

2. Ler: TESTE_PRATICO_2_CAMERAS.md
3. Procurar seu erro na tabela
4. Seguir solução
```

### Cenário 3: "Amanhã vou adicionar as 3 térmicas"

```
1. Ler: AMANHA_ADICIONAR_TERMICAS.md
2. Conectar 3 câmeras à rede
3. Descobrir IPs (nmap)
4. Editar app.py (descomentar 3 blocos)
5. docker-compose restart vigilancia-backend
6. F5 no browser
7. Verificar 5/5 online
```

### Cenário 4: "Quero entender como funciona"

```
1. Ler: README.md (visão geral)
2. Ler: RESUMO_EXECUTIVO.md (decisões)
3. Explorar código em app.py
4. Rodar em Docker e observar
```

---

## 📊 ESTRUTURA DO SISTEMA (Visual)

```
┌─────────────────────────────────────┐
│   VOCÊ AQUI: Computador Local       │
│   Windows / macOS / Linux            │
│   http://localhost:3000              │
└────────┬────────────────────────────┘
         │
    ┌────┴────────────────┐
    │                     │
    ↓                     ↓
┌─────────┐          ┌──────────┐
│ Browser │          │  Docker  │
│ React   │          │  Stack   │
└────┬────┘          └─────┬────┘
     │                     │
     │         ┌───────────┼──────────┐
     │         ↓           ↓          ↓
     │    ┌────────┐  ┌────────┐  ┌────────┐
     │    │FastAPI│  │React   │  │Database│
     │    │Backend │  │Dev     │  │ + Cache│
     └────┤(8000) │  │(3000)  │  │        │
          └────────┘  └────────┘  └────────┘
               │          │
               └──────┬───┘
                      ↓
            ┌──────────────────┐
            │ Câmeras RTSP     │
            ├──────────────────┤
            │ 🎥 Dome 1 (RGB)  │
            │ 🎥 Dome 2 (RGB)  │
            │ 🌡️  Térmica 1-3  │ (amanhã)
            └──────────────────┘
```

---

## 🔑 PONTOS-CHAVE

### Hoje
- ✅ Sistema roda com 2 RGB
- ✅ Mapa interativo funciona
- ✅ Snapshots em tempo real
- ✅ WebSocket de eventos

### Amanhã
- ➕ Descomentar 3 linhas em app.py
- ➕ Preencher 3 IPs
- ➕ Reiniciar backend (1 comando)
- ✅ Sistema com 5 câmeras

### Diferenças Importantes
- RGB: Não tem detecção de pessoas (só movimento)
- Térmica: Detecta pessoas, fogo, objetos

---

## 💾 ARQUIVOS VOCÊ EDITA

### Hoje:
- **Nada** (tudo pronto)

### Amanhã:
- **app.py** linha ~50: descomentar `thermal_1`, `thermal_2`, `thermal_3`
- **app.py** linha ~55,65,75: editar IPs para seus valores reais

### Depois:
- **app.py** linha ~25: ajustar `DETECTION_THRESHOLDS` se falsos positivos
- **App.tsx** linha ~80: ajustar posições no mapa (`position: {x, y}`)

---

## 🎓 APRENDER

### Quick Start (15 min)
1. COMECE_HOJE.md
2. Rodar start.sh / start.bat
3. Explorar UI

### Intermediate (1h)
1. README.md
2. AMANHA_ADICIONAR_TERMICAS.md
3. Editar app.py

### Advanced (>2h)
1. Ler app.py inteiro
2. Entender OpenCV detections
3. Modificar DETECTION_THRESHOLDS
4. Integrar YOLO v8 (futuro)

---

## 🔗 LINKS ÚTEIS

| Recurso | Link |
|---------|------|
| Docker Install | https://www.docker.com/products/docker-desktop |
| FastAPI Docs | https://fastapi.tiangolo.com |
| React Docs | https://react.dev |
| OpenCV | https://docs.opencv.org |
| Hikvision RTSP | https://www.hikvision.com |

---

## ✅ CHECKLIST HOJE

- [ ] Ler COMECE_HOJE.md
- [ ] Rodar start.sh / start.bat
- [ ] Aguardar 30s
- [ ] Abrir http://localhost:3000
- [ ] Ver 2 câmeras online 🟢
- [ ] Clicar em câmera para ver snapshot
- [ ] Verificar timeline vazia (normal)

## ✅ CHECKLIST AMANHÃ

- [ ] Ler AMANHA_ADICIONAR_TERMICAS.md
- [ ] Conectar 3 térmicas à rede
- [ ] Descobrir IPs
- [ ] Editar app.py
- [ ] docker-compose restart vigilancia-backend
- [ ] Verificar 5/5 online
- [ ] Testar detecção com pessoa

---

## 📞 AJUDA

### Problema com Docker
→ Ler: TESTE_PRATICO_2_CAMERAS.md

### Problema com câmeras
→ Terminal: `docker logs vigilancia-backend`

### Quer adicionar térmicas
→ Ler: AMANHA_ADICIONAR_TERMICAS.md

### Quer entender código
→ Ler: README.md

---

## 🎯 RESUMO

```
TODAY (HOJE):
./start.sh → http://localhost:3000 → 2/2 online ✅

TOMORROW (AMANHÃ):
edit app.py → docker restart → 5/5 online ✅

NEXT WEEK (PRÓXIMA SEMANA):
calibrate → test → integrate sensors ✅
```

---

**Você está 90% pronto. Falta só apertar start.sh/start.bat.** 🚀

Boa sorte! 🎬
