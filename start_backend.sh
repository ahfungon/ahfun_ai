#!/bin/bash

echo "=========================================="
echo "启动后端服务"
echo "=========================================="

# 检查端口是否被占用
echo -e "\n1. 检查端口 8080..."
if lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️ 端口 8080 被占用，尝试停止占用进程..."
    
    # 停止旧的后端服务
    pkill -f "uvicorn main:app"
    
    # 停止 nginx（如果存在）
    pkill -f nginx
    
    sleep 2
    
    # 再次检查
    if lsof -i :8080 > /dev/null 2>&1; then
        echo "❌ 无法释放端口 8080，请手动检查"
        lsof -i :8080
        exit 1
    else
        echo "✅ 端口 8080 已释放"
    fi
else
    echo "✅ 端口 8080 可用"
fi

# 启动后端服务
echo -e "\n2. 启动后端服务..."
nohup uvicorn main:app --host 0.0.0.0 --port 8080 > logs/api.log 2>&1 &
BACKEND_PID=$!
echo "后端服务 PID: $BACKEND_PID"

# 等待服务启动
echo -e "\n3. 等待服务启动..."
sleep 3

# 检查服务状态
echo -e "\n4. 检查服务状态..."
if curl -s http://localhost:8080/api/health > /dev/null; then
    echo "✅ 后端服务启动成功"
    
    # 显示健康状态
    echo -e "\n健康状态:"
    curl -s http://localhost:8080/api/health | python -m json.tool | head -20
    
    echo -e "\n=========================================="
    echo "后端服务运行正常"
    echo "访问地址: http://localhost:8080"
    echo "API 文档: http://localhost:8080/docs"
    echo "=========================================="
else
    echo "❌ 后端服务启动失败"
    echo -e "\n查看日志:"
    tail -20 logs/api.log
    exit 1
fi
