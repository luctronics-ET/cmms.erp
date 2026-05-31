#!/bin/bash

################################################################################
# Script de Setup Automatizado - ERP + CMMS + BMS com CoreUI
# Versão: 1.0
# Data: 20/03/2026
################################################################################

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de output
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Banner
echo "================================================================================"
echo "  SETUP ERP + CMMS + BMS - Sistema Integrado com CoreUI"
echo "================================================================================"
echo ""

# Verificar dependências
info "Verificando dependências..."

command -v docker >/dev/null 2>&1 || error "Docker não está instalado!"
if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    error "Docker Compose não está instalado!"
fi
command -v npm >/dev/null 2>&1 || error "NPM não está instalado!"

# Composer via Docker (não requer instalação local)
COMPOSER_CMD="docker run --rm -v \"\$(pwd):/app\" -w /app --user \$(id -u):\$(id -g) composer:latest"

success "Todas as dependências estão instaladas"

# Perguntar nome do projeto
read -p "Nome do projeto [erp-cmms-system]: " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-erp-cmms-system}

# Criar estrutura de diretórios
info "Criando estrutura de diretórios..."
mkdir -p ${PROJECT_NAME}/{docker/{nginx,php,postgres,mosquitto/config},backend,frontend}
cd ${PROJECT_NAME}
success "Estrutura criada"

################################################################################
# CRIAR ARQUIVOS DOCKER
################################################################################

info "Criando arquivo docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: erp_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./backend:/var/www/html
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - app
    networks:
      - erp_network
    restart: unless-stopped

  app:
    build:
      context: ./docker/php
      dockerfile: Dockerfile
    container_name: erp_app
    volumes:
      - ./backend:/var/www/html
      - ./docker/php/php.ini:/usr/local/etc/php/php.ini
    environment:
      - DB_CONNECTION=pgsql
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_DATABASE=erp_cmms_db
      - DB_USERNAME=erp_user
      - DB_PASSWORD=erp_secure_password
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - postgres
      - redis
    networks:
      - erp_network
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: erp_postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      - POSTGRES_DB=erp_cmms_db
      - POSTGRES_USER=erp_user
      - POSTGRES_PASSWORD=erp_secure_password
    networks:
      - erp_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U erp_user -d erp_cmms_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: erp_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --requirepass erp_redis_password
    networks:
      - erp_network
    restart: unless-stopped

  websockets:
    build:
      context: ./docker/php
      dockerfile: Dockerfile
    container_name: erp_websockets
    volumes:
      - ./backend:/var/www/html
    command: php artisan serve --host=0.0.0.0 --port=6001
    ports:
      - "6001:6001"
    depends_on:
      - app
      - redis
    networks:
      - erp_network
    restart: unless-stopped

  mqtt:
    image: eclipse-mosquitto:2
    container_name: erp_mqtt
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./docker/mosquitto/config:/mosquitto/config
      - mqtt_data:/mosquitto/data
    networks:
      - erp_network
    restart: unless-stopped

  queue:
    build:
      context: ./docker/php
      dockerfile: Dockerfile
    container_name: erp_queue
    volumes:
      - ./backend:/var/www/html
    command: php artisan queue:work --sleep=3 --tries=3
    depends_on:
      - app
      - redis
      - postgres
    networks:
      - erp_network
    restart: unless-stopped

  adminer:
    image: adminer:latest
    container_name: erp_adminer
    ports:
      - "8080:8080"
    environment:
      - ADMINER_DEFAULT_SERVER=postgres
    depends_on:
      - postgres
    networks:
      - erp_network
    restart: unless-stopped

networks:
  erp_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  mqtt_data:
EOF
success "docker-compose.yml criado"

info "Criando Dockerfile PHP..."
cat > docker/php/Dockerfile << 'EOF'
FROM php:8.2-fpm-alpine

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN apk add --no-cache \
    git curl libpng-dev libzip-dev zip unzip \
    postgresql-dev oniguruma-dev icu-dev \
    freetype-dev libjpeg-turbo-dev libwebp-dev \
    supervisor nodejs npm

RUN docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp \
    && docker-php-ext-install \
    pdo pdo_pgsql pgsql mbstring zip exif \
    pcntl bcmath gd intl opcache

RUN pecl install redis && docker-php-ext-enable redis

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

RUN addgroup -g ${GROUP_ID} laravel \
    && adduser -D -u ${USER_ID} -G laravel laravel

WORKDIR /var/www/html

COPY php.ini /usr/local/etc/php/conf.d/custom.ini

RUN chown -R laravel:laravel /var/www/html

USER laravel

EXPOSE 9000

CMD ["php-fpm"]
EOF
success "Dockerfile criado"

info "Criando php.ini..."
cat > docker/php/php.ini << 'EOF'
[PHP]
memory_limit = 512M
upload_max_filesize = 100M
post_max_size = 100M
max_execution_time = 300
max_input_time = 300
date.timezone = America/Sao_Paulo
display_errors = On
display_startup_errors = On
error_reporting = E_ALL
log_errors = On
error_log = /var/log/php_errors.log
session.save_handler = redis
session.save_path = "tcp://redis:6379?auth=erp_redis_password"
session.gc_maxlifetime = 86400
opcache.enable = 1
opcache.memory_consumption = 256
opcache.interned_strings_buffer = 16
opcache.max_accelerated_files = 20000
realpath_cache_size = 4096K
realpath_cache_ttl = 600
expose_php = Off
max_input_vars = 3000
EOF
success "php.ini criado"

info "Criando configuração Nginx..."
cat > docker/nginx/default.conf << 'EOF'
server {
    listen 80;
    server_name localhost;
    root /var/www/html/public;
    index index.php index.html;
    charset utf-8;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    client_max_body_size 100M;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location = /favicon.ico { access_log off; log_not_found off; }
    location = /robots.txt  { access_log off; log_not_found off; }

    error_page 404 /index.php;

    location ~ \.php$ {
        try_files $uri =404;
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass app:9000;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_buffering off;
        fastcgi_read_timeout 300;
        fastcgi_send_timeout 300;
    }

    location ~ /\.(?!well-known).* {
        deny all;
    }

    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /ws {
        proxy_pass http://websockets:6001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF
success "Nginx config criado"

info "Criando configuração Mosquitto..."
cat > docker/mosquitto/config/mosquitto.conf << 'EOF'
listener 1883
protocol mqtt
listener 9001
protocol websockets
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
log_type all
log_timestamp true
max_connections -1
max_queued_messages 1000
allow_anonymous true
max_queued_bytes 0
message_size_limit 0
max_inflight_messages 20
max_keepalive 65535
EOF
success "Mosquitto config criado"

info "Criando init.sql PostgreSQL..."
cat > docker/postgres/init.sql << 'EOF'
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
EOF
success "init.sql criado"

################################################################################
# CRIAR PROJETO LARAVEL
################################################################################

info "Criando projeto Laravel..."
cd backend
docker run --rm --dns 8.8.8.8 -v "$(pwd):/app" -w /app --user "$(id -u):$(id -g)" composer:latest create-project --prefer-dist --no-dev laravel/laravel . --no-interaction
success "Laravel instalado"

info "Instalando dependências Laravel..."
docker run --rm --dns 8.8.8.8 -v "$(pwd):/app" -w /app --user "$(id -u):$(id -g)" composer:latest require laravel/sanctum spatie/laravel-permission --no-interaction -W
success "Dependências instaladas"

info "Configurando .env Laravel..."
cat > .env << 'EOF'
APP_NAME="ERP CMMS"
APP_ENV=local
APP_KEY=
APP_DEBUG=true
APP_URL=http://localhost

DB_CONNECTION=pgsql
DB_HOST=postgres
DB_PORT=5432
DB_DATABASE=erp_cmms_db
DB_USERNAME=erp_user
DB_PASSWORD=erp_secure_password

BROADCAST_DRIVER=redis
CACHE_DRIVER=redis
FILESYSTEM_DISK=local
QUEUE_CONNECTION=redis
SESSION_DRIVER=redis
SESSION_LIFETIME=120

REDIS_HOST=redis
REDIS_PASSWORD=erp_redis_password
REDIS_PORT=6379

MAIL_MAILER=smtp
MAIL_HOST=mailhog
MAIL_PORT=1025
MAIL_USERNAME=null
MAIL_PASSWORD=null
MAIL_ENCRYPTION=null
MAIL_FROM_ADDRESS="noreply@erp.local"
MAIL_FROM_NAME="${APP_NAME}"
EOF

APP_KEY="base64:$(openssl rand -base64 32)"
sed -i "s|^APP_KEY=|APP_KEY=${APP_KEY}|" .env
success "Laravel configurado"

cd ..

################################################################################
# CRIAR PROJETO VUE
################################################################################

info "Criando projeto Vue.js..."
cd frontend
npm create vite@latest . -- --template vue --force
success "Vue.js criado"

info "Instalando dependências Vue..."
npm install --silent
npm install @coreui/vue @coreui/icons @coreui/icons-vue @coreui/chartjs chart.js vue-router@4 vuex@4 axios sass --silent
success "Dependências Vue instaladas"

info "Criando estrutura frontend..."
mkdir -p src/{router,store/modules,plugins,layouts,views,components,assets/scss}

# package.json
cat > package.json << 'EOF'
{
  "name": "erp-cmms-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.3.4",
    "vue-router": "^4.2.5",
    "vuex": "^4.1.0",
    "@coreui/vue": "^5.0.0",
    "@coreui/icons": "^3.0.1",
    "@coreui/icons-vue": "^2.0.1",
    "@coreui/chartjs": "^4.0.0",
    "chart.js": "^4.4.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.4.0",
    "vite": "^4.5.0",
    "sass": "^1.69.5"
  }
}
EOF

# vite.config.js com alias @ para src/
cat > vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
EOF

# .env frontend
cat > .env << 'EOF'
VITE_API_URL=http://localhost/api
EOF

# src/main.js
cat > src/main.js << 'EOF'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import CoreuiVue from '@coreui/vue'
import CIcon from '@coreui/icons-vue'
import '@coreui/coreui/dist/css/coreui.min.css'

const app = createApp(App)
app.use(router)
app.use(store)
app.use(CoreuiVue)
app.component('CIcon', CIcon)
app.mount('#app')
EOF

# src/router/index.js
cat > src/router/index.js << 'EOF'
import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
EOF

# src/store/index.js
cat > src/store/index.js << 'EOF'
import { createStore } from 'vuex'

export default createStore({
  state: {
    loading: false
  },
  mutations: {
    SET_LOADING(state, status) {
      state.loading = status
    }
  }
})
EOF

# src/plugins/axios.js
cat > src/plugins/axios.js << 'EOF'
import axios from 'axios'

const instance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost/api',
  timeout: 30000
})

instance.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default instance
EOF

# View básica
mkdir -p src/views
cat > src/views/Dashboard.vue << 'EOF'
<template>
  <div>
    <h1>Dashboard ERP + CMMS + BMS</h1>
    <p>Sistema instalado com sucesso!</p>
  </div>
</template>

<script>
export default {
  name: 'Dashboard'
}
</script>
EOF

success "Estrutura frontend criada"

cd ..

################################################################################
# README
################################################################################

info "Criando README.md..."
cat > README.md << 'EOF'
# Sistema ERP + CMMS + BMS

Sistema integrado de gestão empresarial com CoreUI.

## Instalação

```bash
# Iniciar containers
docker-compose up -d

# Executar migrations
docker exec -it erp_app php artisan migrate:fresh --seed

# Build frontend
cd frontend && npm run build
```

## Acesso

- **Frontend**: http://localhost
- **Adminer**: http://localhost:8080
- **WebSockets**: ws://localhost:6001

## Credenciais Padrão

- Email: admin@example.com
- Senha: password

EOF
success "README.md criado"

################################################################################
# FINALIZAÇÃO
################################################################################

echo ""
echo "================================================================================"
echo -e "${GREEN}  SETUP CONCLUÍDO! Iniciando ambiente...${NC}"
echo "================================================================================"
echo ""

info "Subindo containers Docker..."
${COMPOSE_CMD} up -d
success "Containers iniciados"

info "Aguardando banco de dados ficar pronto (20s)..."
sleep 20

info "Executando migrations e seeders..."
docker exec erp_app php artisan migrate:fresh --seed --force
success "Banco de dados configurado"

info "Abrindo sistema no navegador..."
xdg-open http://localhost 2>/dev/null || open http://localhost 2>/dev/null || true

echo ""
echo "================================================================================"
echo -e "${GREEN}  SISTEMA DISPONÍVEL EM: http://localhost${NC}"
echo -e "${GREEN}  Adminer DB:            http://localhost:8080${NC}"
echo -e "${GREEN}  WebSockets:            ws://localhost:6001${NC}"
echo "================================================================================"
