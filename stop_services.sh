#!/bin/bash

# 双Agent对话平台 - 服务停止脚本

echo "🛑 停止双Agent对话平台服务..."

if [ ! -f ".pids" ]; then
    echo "⚠️  未找到 PID 文件，尝试通过端口查找进程..."
    
    # 查找并停止占用端口的进程
    API_PID=$(lsof -ti:8000)
    FRONTEND_PID=$(lsof -ti:8080)
    
    if [ ! -z "$API_PID" ]; then
        echo "停止 API 进程 (PID: $API_PID)..."
        kill $API_PID 2>/dev/null
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "停止前端服务器 (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    # 停止 Celery 进程
    pkill -f "celery.*worker" 2>/dev/null
    pkill -f "celery.*beat" 2>/dev/null
    
else
    # 从文件读取 PID 并停止
    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "停止进程 PID: $pid"
            kill $pid 2>/dev/null
        fi
    done < .pids
    
    rm .pids
fi

# 等待进程完全停止
sleep 2

echo "✅ 所有服务已停止"
