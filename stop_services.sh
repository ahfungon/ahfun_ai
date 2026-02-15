#!/bin/bash

echo "=========================================="
echo "停止双智能体对话平台服务"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 停止 Nginx
echo ""
echo -e "${YELLOW}停止 Nginx...${NC}"
if pgrep nginx > /dev/null; then
    nginx -s stop 2>/dev/null || true
    sleep 1
    if pgrep nginx > /dev/null; then
        echo -e "${RED}✗ Nginx 停止失败，尝试强制停止${NC}"
        pkill -9 nginx || true
    else
        echo -e "${GREEN}✓ Nginx 已停止${NC}"
    fi
else
    echo -e "${YELLOW}Nginx 未运行${NC}"
fi

# 停止 FastAPI
echo ""
echo -e "${YELLOW}停止 FastAPI...${NC}"
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        kill $API_PID
        sleep 2
        if ps -p $API_PID > /dev/null 2>&1; then
            kill -9 $API_PID
        fi
        echo -e "${GREEN}✓ FastAPI 已停止 (PID: $API_PID)${NC}"
    else
        echo -e "${YELLOW}FastAPI 未运行${NC}"
    fi
    rm -f logs/api.pid
else
    pkill -f "uvicorn main:app" || true
    echo -e "${GREEN}✓ FastAPI 进程已清理${NC}"
fi

# 停止 Celery Worker
echo ""
echo -e "${YELLOW}停止 Celery Worker...${NC}"
if [ -f "logs/worker.pid" ]; then
    WORKER_PID=$(cat logs/worker.pid)
    if ps -p $WORKER_PID > /dev/null 2>&1; then
        kill $WORKER_PID
        sleep 2
        if ps -p $WORKER_PID > /dev/null 2>&1; then
            kill -9 $WORKER_PID
        fi
        echo -e "${GREEN}✓ Celery Worker 已停止 (PID: $WORKER_PID)${NC}"
    else
        echo -e "${YELLOW}Celery Worker 未运行${NC}"
    fi
    rm -f logs/worker.pid
else
    pkill -f "celery.*worker" || true
    echo -e "${GREEN}✓ Celery Worker 进程已清理${NC}"
fi

# 停止 Celery Beat
echo ""
echo -e "${YELLOW}停止 Celery Beat...${NC}"
if [ -f "logs/beat.pid" ]; then
    BEAT_PID=$(cat logs/beat.pid)
    if ps -p $BEAT_PID > /dev/null 2>&1; then
        kill $BEAT_PID
        sleep 2
        if ps -p $BEAT_PID > /dev/null 2>&1; then
            kill -9 $BEAT_PID
        fi
        echo -e "${GREEN}✓ Celery Beat 已停止 (PID: $BEAT_PID)${NC}"
    else
        echo -e "${YELLOW}Celery Beat 未运行${NC}"
    fi
    rm -f logs/beat.pid
else
    pkill -f "celery.*beat" || true
    echo -e "${GREEN}✓ Celery Beat 进程已清理${NC}"
fi

# 清理 Nginx 配置
if [ -f "nginx_local.conf" ]; then
    rm -f nginx_local.conf
    echo -e "${GREEN}✓ Nginx 配置已清理${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}所有服务已停止${NC}"
echo "=========================================="
