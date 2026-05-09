@echo off
REM 🚀 SCRIPT DE INICIALIZAÇÃO - WINDOWS
REM Uso: start.bat (duplo clique ou cmd)

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════╗
echo ║  🎥 SISTEMA DE VIGILÂNCIA INTEGRADO    ║
echo ║        ^(2 Câmeras PTZ - Teste^)         ║
echo ╚════════════════════════════════════════╝
echo.

REM 1. Verificar Docker
echo 1️⃣  Verificando Docker...

where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker não encontrado!
    echo Instale em: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

where docker-compose >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker Compose não encontrado!
    pause
    exit /b 1
)

echo ✅ Docker OK
docker --version
docker-compose --version

REM 2. Parar containers antigos
echo.
echo 2️⃣  Limpando containers antigos...

docker-compose down --remove-orphans 2>nul
echo ✅ Limpeza concluída

REM 3. Iniciar stack
echo.
echo 3️⃣  Iniciando stack ^(FastAPI + React + DB^)...

docker-compose up -d
echo ✅ Containers iniciados

REM 4. Aguardar backend
echo.
echo 4️⃣  Aguardando serviços ficarem online...

setlocal enabledelayedexpansion
set ATTEMPT=0
set MAX_ATTEMPTS=30

:WAIT_BACKEND
if !ATTEMPT! geq !MAX_ATTEMPTS! goto TIMEOUT
set /a ATTEMPT+=1

timeout /t 1 /nobreak >nul

for /f %%A in ('curl -s http://localhost:8000/health 2^>nul ^| find "ok"') do (
    goto BACKEND_OK
)

if !ATTEMPT! equ 30 goto WAIT_BACKEND

:BACKEND_OK
echo ✅ Backend online ^(!ATTEMPT!s^)

REM 5. Status
echo.
echo 5️⃣  Status dos serviços:
echo.
docker-compose ps
echo.

REM 6. Informações
echo ════════════════════════════════════════
echo 🎉 SISTEMA INICIADO COM SUCESSO!
echo ════════════════════════════════════════
echo.
echo 📍 Acesso:
echo    🌐 Frontend:    http://localhost:3000
echo    🔌 Backend API: http://localhost:8000
echo    📊 API Docs:    http://localhost:8000/docs
echo    🗄️  PgAdmin:    http://localhost:5050 ^(admin/admin123^)
echo.
echo 📋 Próximos passos:
echo    1. Abrir http://localhost:3000 no navegador
echo    2. Verificar se 2 câmeras aparecem como 🟢 online
echo    3. Clicar em uma câmera para ver stream
echo.
echo ⏹️  Para parar:
echo    docker-compose down
echo.
echo 📝 Ver logs:
echo    docker logs -f vigilancia-backend
echo    docker logs -f vigilancia-frontend-dev
echo.

REM 7. Abrir browser
echo Abrindo browser em 3 segundos...
timeout /t 3 /nobreak >nul

start http://localhost:3000

echo.
echo ✅ Pronto!
echo.
pause

goto :EOF

:TIMEOUT
echo ⚠️  Timeout aguardando backend
echo Verifique com: docker logs vigilancia-backend
pause
goto :EOF
