#!/bin/bash
# 🚀 SCRIPT DE INICIALIZAÇÃO - SISTEMA DE VIGILÂNCIA
# 
# Uso: ./start.sh
# 
# O que faz:
# 1. Valida que Docker está instalado
# 2. Para containers antigos se existirem
# 3. Inicia stack completa
# 4. Aguarda serviços ficarem online
# 5. Abre browser em http://localhost:3000

set -e  # Parar se algo falhar

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║  🎥 SISTEMA DE VIGILÂNCIA INTEGRADO    ║"
echo "║        (2 Câmeras PTZ - Teste)         ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Verificar Docker
echo -e "${BLUE}1️⃣  Verificando Docker...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não encontrado!${NC}"
    echo "Instale em: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose não encontrado!${NC}"
    echo "Instale em: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker OK${NC}"
echo "   $(docker --version)"
echo "   $(docker-compose --version)"

# 2. Parar containers antigos
echo -e "\n${BLUE}2️⃣  Limpando containers antigos...${NC}"

if docker-compose ps | grep -q "vigilancia"; then
    echo "   Parando containers..."
    docker-compose down --remove-orphans 2>/dev/null || true
    echo -e "${GREEN}✅ Limpeza concluída${NC}"
else
    echo -e "${GREEN}✅ Nenhum container antigo${NC}"
fi

# 3. Iniciar stack
echo -e "\n${BLUE}3️⃣  Iniciando stack (FastAPI + React + DB)...${NC}"

docker-compose up -d

echo -e "${GREEN}✅ Containers iniciados${NC}"

# 4. Aguardar serviços ficarem online
echo -e "\n${BLUE}4️⃣  Aguardando serviços ficarem online...${NC}"

MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    # Verificar se backend respondeu
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend online${NC}"
        break
    fi
    
    if [ $((ATTEMPT % 5)) -eq 0 ]; then
        echo "   Tentativa $ATTEMPT/$MAX_ATTEMPTS..."
    fi
    
    sleep 1
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${YELLOW}⚠️  Timeout aguardando backend${NC}"
else
    echo "   Tempo total: ${ATTEMPT}s"
fi

# 5. Mostrar status
echo -e "\n${BLUE}5️⃣  Status dos serviços:${NC}"

docker-compose ps --format "table {{.Names}}\t{{.Status}}"

# 6. Informações de acesso
echo -e "\n${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 SISTEMA INICIADO COM SUCESSO!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}\n"

echo "📍 Acesso:"
echo "   🌐 Frontend:    http://localhost:3000"
echo "   🔌 Backend API: http://localhost:8000"
echo "   📊 API Docs:    http://localhost:8000/docs"
echo "   🗄️  PgAdmin:    http://localhost:5050 (admin/admin123)"

echo -e "\n📋 Próximos passos:"
echo "   1. Abrir http://localhost:3000 no navegador"
echo "   2. Verificar se 2 câmeras aparecem como 🟢 online"
echo "   3. Clicar em uma câmera para ver stream"

echo -e "\n⏹️  Para parar:"
echo "   docker-compose down"

echo -e "\n📝 Ver logs:"
echo "   docker logs -f vigilancia-backend"
echo "   docker logs -f vigilancia-frontend-dev"

echo -e "\n${BLUE}Abrindo browser em 3 segundos...${NC}\n"

sleep 3

# 7. Tentar abrir browser
if command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:3000
elif command -v open &> /dev/null; then
    # macOS
    open http://localhost:3000
elif command -v start &> /dev/null; then
    # Windows
    start http://localhost:3000
else
    echo "Abra manualmente: http://localhost:3000"
fi

echo -e "${GREEN}✅ Pronto!${NC}"
