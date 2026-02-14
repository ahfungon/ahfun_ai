#!/bin/bash

# 双Agent对话平台 - 服务启动脚本

echo "🚀 启动双Agent对话平台服务..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查 Redis 是否运行
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis 未运行，尝试启动..."
    if command -v redis-server > /dev/null 2>&1; then
        redis-server --daemonize yes
        sleep 2
    else
        echo "❌ Redis 未安装，请先安装 Redis"
        exit 1
    fi
fi

# 检查 PostgreSQL 是否运行
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL 未运行，请先启动 PostgreSQL"
    exit 1
fi

# 启动后端 API
echo "📡 启动后端 API (端口 8000)..."
python main.py > logs/api.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"

# 等待 API 启动
sleep 3

# 检查 API 是否启动成功
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ 后端 API 启动成功"
else
    echo "❌ 后端 API 启动失败，请检查日志: logs/api.log"
    exit 1
fi

# 启动 Celery Worker
echo "⚙️  启动 Celery Worker..."
celery -A workers.celery_app worker --loglevel=info > logs/worker.log 2>&1 &
WORKER_PID=$!
echo "   PID: $WORKER_PID"

# 启动 Celery Beat
echo "⏰ 启动 Celery Beat..."
celery -A workers.celery_app beat --loglevel=info > logs/beat.log 2>&1 &
BEAT_PID=$!
echo "   PID: $BEAT_PID"

# 启动前端服务器
echo "🌐 启动前端服务器 (端口 8080)..."
cd frontend
python3 -m http.server 8080 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   PID: $FRONTEND_PID"

# 保存 PID 到文件
echo "$API_PID" > .pids
echo "$WORKER_PID" >> .pids
echo "$BEAT_PID" >> .pids
echo "$FRONTEND_PID" >> .pids

echo ""
echo "✨ 所有服务启动完成！"
echo ""
echo "📍 访问地址："
echo "   - 前端查看界面: http://localhost:8080/index.html"
echo "   - 前端管理面板: http://localhost:8080/admin.html"
echo "   - 后端API文档: http://localhost:8000/docs"
echo "   - 健康检查: http://localhost:8000/api/health"
echo ""
echo "📝 日志文件："
echo "   - API: logs/api.log"
echo "   - Worker: logs/worker.log"
echo "   - Beat: logs/beat.log"
echo "   - Frontend: logs/frontend.log"
echo ""
echo "🛑 停止服务: ./stop_services.sh"
