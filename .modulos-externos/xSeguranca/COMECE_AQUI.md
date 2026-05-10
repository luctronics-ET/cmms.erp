# 🚀 COMEÇAR TESTE COM SUAS 2 CÂMERAS - RESUMO

## ⏱️ 5 MINUTOS PARA VALIDAR TUDO

---

## O que você tem:

✅ **Dome 1** (192.168.0.198) - RGB, não térmica
✅ **Dome 2** (192.168.0.199) - Térmica (detecta pessoa, fogo, objetos)

---

## Teste 1: Validar conectividade (30 seg)

```bash
# Terminal, rodar:
ping 192.168.0.198
ping 192.168.0.199

# Resultado esperado: respostas em 1-5ms
```

**Se não responder:**
- Câmera desligada?
- IP errado?
- Wifi/ethernet conectado?

---

## Teste 2: Rodar script de teste (2 min)

```bash
# 1. Baixar script (já está em outputs/)
# Arquivo: test_suas_cameras.py

# 2. Rodar
python test_suas_cameras.py

# 3. Resultado esperado:
# ✅ PASSOU Dome 1 - Entrada
# ✅ PASSOU Dome 2 - Perímetro (Térmica)
# Resultado: 2/2 câmeras passaram ✅
```

**Se falhar em alguma:**
- Verificar IP/senha em CAMERAS_CONFIG
- Ou usar arquivo: SUAS_CAMERAS_CONFIG.txt (já pronto)

---

## Teste 3: Ver snapshots (1 min)

```bash
# Depois do teste, abrir:
./snapshots/dome_1_latest.jpg
./snapshots/dome_2_latest.jpg

# Devem mostrar imagens ao vivo das câmeras
```

---

## Teste 4: Full Stack com Docker (2 min setup)

```bash
# 1. Copiar sua config em app.py (usar SUAS_CAMERAS_CONFIG.txt)
# 2. Rodar:
docker-compose up -d

# 3. Aguardar 30s
# 4. Abrir: http://localhost:3000

# Deve mostrar:
# - Mapa com 2 ícones 🎥
# - Status "2/2 câmeras online"
# - Timeline de eventos (se houver movimento)
```

---

## Próximos 30 minutos (depois dos testes ✅)

### Calibrar Detecção Térmica

```python
# Editar em app.py (DETECTION_THRESHOLDS):
"thermal_person": 37,   # Temperatura mínima
"thermal_fire": 60,     # Temperatura fogo
```

**Como testar:**
1. Pessoa perto da Dome 2 (térmica)
2. Observar se aparece na timeline
3. Ajustar thresholds se necessário (35-40 para pessoa)

---

## Checklist Rápido

- [ ] Ping 192.168.0.198 responde
- [ ] Ping 192.168.0.199 responde
- [ ] `python test_suas_cameras.py` retorna 2/2 ✅
- [ ] Snapshots aparecem em `./snapshots/`
- [ ] `docker-compose up -d` inicia sem erro
- [ ] http://localhost:3000 abre no navegador
- [ ] 2 câmeras aparecem no mapa com status "online" 🟢

---

## Se tudo passar ✅

**Parabéns! Sistema funcionando.**

Próximos passos:
1. Calibrar thresholds térmicos (15 min)
2. Configurar mapa (60 min)
3. Testar ONVIF PTZ control (opcional)

---

## Se algo falhar ❌

Usar arquivo: **TESTE_PRATICO_2_CAMERAS.md**
(Troubleshooting detalhado)

---

**Comece agora: `python test_suas_cameras.py`** 🚀

---

Arquivos necessários:
- ✅ test_suas_cameras.py
- ✅ SUAS_CAMERAS_CONFIG.txt
- ✅ app.py (editar IPs se precisar)
- ✅ docker-compose.yml
- ✅ TESTE_PRATICO_2_CAMERAS.md (troubleshooting)
