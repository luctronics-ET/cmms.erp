# 🚀 COMEÇAR AGORA - 2 Câmeras RGB

## ⏱️ 3 minutos para tudo funcionar

---

## 1️⃣ Pré-requisitos

```bash
✅ Docker Desktop instalado
✅ 2 câmeras Hikvision na rede (192.168.0.198, 192.168.0.199)
✅ Computador com pelo menos 4GB RAM livre
```

**Não tém Docker?** https://www.docker.com/products/docker-desktop

---

## 2️⃣ Rodar Tudo em 1 Comando

### Linux/macOS:

```bash
chmod +x start.sh
./start.sh
```

### Windows:

```bash
# Duplo clique em: start.bat
# Ou abrir CMD aqui e rodar: start.bat
```

---

## 3️⃣ O Que Vai Acontecer

```
1. Docker verifica
2. Stack inicia (backend + frontend + banco de dados)
3. Aguarda ~30 segundos
4. Browser abre em http://localhost:3000
5. Você vê mapa com 2 câmeras 🎉
```

---

## 4️⃣ Validar Que Funciona

No browser (http://localhost:3000):

```
✅ Mapa aparece
✅ 2 ícones de câmera: 🎥 🎥
✅ Status: "🟢 2/2 câmeras online"
✅ Timeline vazia (normal, ainda)
```

**Clicar em uma câmera:**
- Abre modal com snapshot em tempo real
- Atualiza a cada 2 segundos
- Se PTZ, mostra setas de controle

---

## 5️⃣ Se Não Funcionar

### Câmera não conecta (status 🔴)

```bash
# Terminal:
ping 192.168.0.198
ping 192.168.0.199

# Resultado esperado: resposta em 1-5ms
# Se não responder: IP errado ou câmera desligada
```

### Browser não abre

Abrir manualmente: http://localhost:3000

### Erro no Docker

```bash
# Ver logs
docker logs vigilancia-backend

# Parar tudo e tentar novamente
docker-compose down
docker-compose up -d
```

---

## 6️⃣ Controlar Tudo

### Ver status

```bash
docker-compose ps
```

### Ver logs backend

```bash
docker logs -f vigilancia-backend
```

### Ver logs frontend

```bash
docker logs -f vigilancia-frontend-dev
```

### Parar tudo

```bash
docker-compose down
```

### Rodar novamente

```bash
./start.sh  # ou ./start.bat no Windows
```

---

## 7️⃣ Amanhã: Adicionar as 3 Térmicas

Arquivo: **AMANHA_ADICIONAR_TERMICAS.md**

Resumo rápido:
1. Conectar 3 térmicas à rede
2. Descobrir IPs (ping/nmap)
3. Editar `app.py` (descomentar 3 blocos)
4. `docker-compose restart vigilancia-backend`
5. Recarregar browser (F5)
6. Verificar 5/5 online

**5 minutos, sem parar o sistema.**

---

## 📍 URLs Úteis

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Vigilância** | http://localhost:3000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **API Health** | http://localhost:8000/health | - |
| **PgAdmin** | http://localhost:5050 | admin / admin123 |

---

## 🔧 Estrutura de Arquivos

```
├── app.py                    ← Backend (FastAPI)
├── App.tsx + App.css         ← Frontend (React)
├── docker-compose.yml        ← Orquestração
├── start.sh / start.bat      ← Inicializar (você está aqui)
└── AMANHA_ADICIONAR_TERMICAS.md  ← Para amanhã
```

---

## 💡 Dicas

1. **Sistema fica online 24h**: `docker-compose up -d` roda em background
2. **Logs em tempo real**: `docker logs -f vigilancia-backend` ajuda a debugar
3. **Sem perder dados**: PostgreSQL persiste tudo (histórico de eventos)
4. **Fácil testar**: Mudar `docker-compose.yml` porta e subir paralelo

---

## 🎬 Começar Agora

```bash
# Linux/macOS:
./start.sh

# Windows:
start.bat
```

**Pronto em 3 minutos!** 🚀

---

Qualquer problema durante execução → arquivo de debug em terminal mostrará exatamente o que está errado.

Boa sorte! 🎥
