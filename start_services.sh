#!/bin/bash
set -e

echo "=========================================="
echo "双智能体对话平台 - 本地开发环境启动"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -f "main.py" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 1. 检查 Redis
echo ""
echo -e "${YELLOW}[1/6] 检查 Redis 服务...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis 已运行${NC}"
else
    echo -e "${YELLOW}启动 Redis...${NC}"
    if command -v brew &> /dev/null; then
        # macOS with Homebrew
        brew services start redis
    else
        # Linux
        sudo systemctl start redis
    fi
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis 启动成功${NC}"
    else
        echo -e "${RED}✗ Redis 启动失败${NC}"
        exit 1
    fi
fi

# 2. 检查 PostgreSQL
echo ""
echo -e "${YELLOW}[2/6] 检查 PostgreSQL 服务...${NC}"

# 检查 PostgreSQL 是否运行
PG_RUNNING=false
if command -v psql &> /dev/null; then
    if psql -h localhost -U postgres -d postgres -c "SELECT 1" > /dev/null 2>&1; then
        PG_RUNNING=true
    elif psql -h localhost -U $USER -d postgres -c "SELECT 1" > /dev/null 2>&1; then
        PG_RUNNING=true
    fi
fi

if [ "$PG_RUNNING" = true ]; then
    echo -e "${GREEN}✓ PostgreSQL 已运行${NC}"
else
    echo -e "${YELLOW}PostgreSQL 未响应，尝试启动...${NC}"
    if command -v brew &> /dev/null; then
        # macOS with Homebrew
        if brew list | grep -q "postgresql@15"; then
            brew services restart postgresql@15
        elif brew list | grep -q "postgresql@14"; then
            brew services restart postgresql@14
        elif brew list | grep -q "postgresql"; then
            brew services restart postgresql
        fi
    else
        # Linux
        sudo systemctl restart postgresql
    fi
    sleep 3
    echo -e "${GREEN}✓ PostgreSQL 已启动${NC}"
fi

# 3. 激活虚拟环境
echo ""
echo -e "${YELLOW}[3/6] 激活 Python 虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi
source venv/bin/activate
echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
echo "  Python: $(which python)"
echo "  版本: $(python --version)"

# 4. 安装依赖
echo ""
echo -e "${YELLOW}[4/6] 检查 Python 依赖...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ 依赖已安装${NC}"

# 5. 创建日志目录
echo ""
echo -e "${YELLOW}[5/6] 创建日志目录...${NC}"
mkdir -p logs
chmod 755 logs
echo -e "${GREEN}✓ 日志目录已创建${NC}"

# 6. 启动服务
echo ""
echo -e "${YELLOW}[6/6] 启动服务...${NC}"

# 停止旧进程
echo "停止旧进程..."
pkill -f "uvicorn main:app" || true
pkill -f "celery.*worker" || true
pkill -f "celery.*beat" || true
sleep 2

# 启动 FastAPI (后端 8000 端口)
echo "启动 FastAPI 服务 (端口 8000)..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!
echo "  PID: $API_PID"

# 启动 Celery Worker (监听所有队列)
echo "启动 Celery Worker (监听 default, summary_jobs, periodic_tasks 队列)..."
nohup celery -A workers.celery_app worker --loglevel=info -Q default,summary_jobs,periodic_tasks > logs/worker.log 2>&1 &
WORKER_PID=$!
echo "  PID: $WORKER_PID"

# 启动 Celery Beat
echo "启动 Celery Beat..."
nohup celery -A workers.celery_app beat --loglevel=info > logs/beat.log 2>&1 &
BEAT_PID=$!
echo "  PID: $BEAT_PID"

# 等待服务启动
echo ""
echo "等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo -e "${YELLOW}检查服务状态...${NC}"

if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✓ FastAPI 运行中 (PID: $API_PID)${NC}"
else
    echo -e "${RED}✗ FastAPI 启动失败${NC}"
    echo "查看日志: tail -f logs/api.log"
fi

if ps -p $WORKER_PID > /dev/null; then
    echo -e "${GREEN}✓ Celery Worker 运行中 (PID: $WORKER_PID)${NC}"
else
    echo -e "${RED}✗ Celery Worker 启动失败${NC}"
    echo "查看日志: tail -f logs/worker.log"
fi

if ps -p $BEAT_PID > /dev/null; then
    echo -e "${GREEN}✓ Celery Beat 运行中 (PID: $BEAT_PID)${NC}"
else
    echo -e "${RED}✗ Celery Beat 启动失败${NC}"
    echo "查看日志: tail -f logs/beat.log"
fi

# 启动 Nginx (8080 端口)
echo ""
echo -e "${YELLOW}配置并启动 Nginx (端口 8080)...${NC}"

# 创建 Nginx 配置
NGINX_CONF="nginx_local.conf"
cat > $NGINX_CONF <<'NGINXEOF'
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include       /usr/local/etc/nginx/mime.types;
    default_type  application/octet-stream;

    sendfile on;
    keepalive_timeout 65;

    server {
        listen 8080;
        server_name localhost;

        client_max_body_size 10M;

        # 前端静态文件
        location / {
            root REPLACE_PROJECT_PATH/frontend;
            try_files $uri $uri/ /monitor.html;
            index monitor.html;
        }

        # 静态资源
        location /static/ {
            alias REPLACE_PROJECT_PATH/static/;
        }

        # API 代理
        location /api/ {
            proxy_pass http://127.0.0.1:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        # API 文档
        location /docs {
            proxy_pass http://127.0.0.1:8000/docs;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /redoc {
            proxy_pass http://127.0.0.1:8000/redoc;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /openapi.json {
            proxy_pass http://127.0.0.1:8000/openapi.json;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
NGINXEOF

# 替换项目路径
PROJECT_PATH=$(pwd)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|REPLACE_PROJECT_PATH|$PROJECT_PATH|g" $NGINX_CONF
else
    sed -i "s|REPLACE_PROJECT_PATH|$PROJECT_PATH|g" $NGINX_CONF
fi

# 检查 Nginx 是否已安装
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}✗ Nginx 未安装${NC}"
    echo "macOS 安装: brew install nginx"
    echo "Ubuntu 安装: sudo apt install nginx"
    echo ""
    echo -e "${YELLOW}跳过 Nginx 配置，你可以直接访问:${NC}"
    echo "  后端 API: http://localhost:8000/docs"
    echo "  前端页面: 需要手动用浏览器打开 frontend/monitor_v2.html"
else
    # 停止现有 Nginx
    nginx -s stop 2>/dev/null || true
    pkill nginx 2>/dev/null || true
    sleep 1
    
    # 启动 Nginx
    nginx -c $(pwd)/$NGINX_CONF
    
    sleep 1
    if pgrep nginx > /dev/null; then
        echo -e "${GREEN}✓ Nginx 运行中 (端口 8080)${NC}"
    else
        echo -e "${RED}✗ Nginx 启动失败${NC}"
        echo "尝试手动启动: nginx -c $(pwd)/$NGINX_CONF"
        echo "查看错误: nginx -t -c $(pwd)/$NGINX_CONF"
    fi
fi

# 保存 PID 到文件
echo $API_PID > logs/api.pid
echo $WORKER_PID > logs/worker.pid
echo $BEAT_PID > logs/beat.pid

echo ""
echo "=========================================="
echo -e "${GREEN}启动完成！${NC}"
echo "=========================================="
echo ""
echo "访问地址："
echo "  🌐 前端监控 (新版): http://localhost:8080"
echo "  🌐 前端监控 (旧版): http://localhost:8080/monitor.html"
echo "  💬 聊天界面 (新版): http://localhost:8080/index_v2.html"
echo "  💬 聊天界面 (旧版): http://localhost:8080/index.html"
echo "  🔧 管理后台: http://localhost:8080/admin.html"
echo "  📚 API 文档: http://localhost:8080/docs"
echo ""
echo "日志文件："
echo "  API: tail -f logs/api.log"
echo "  Worker: tail -f logs/worker.log"
echo "  Beat: tail -f logs/beat.log"
echo ""
echo "停止服务："
echo "  ./stop_services.sh"
echo ""
echo "=========================================="
