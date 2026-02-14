#!/bin/bash

# 双Agent对话平台 - 服务状态检查脚本

echo "🔍 检查服务状态..."
echo ""

# 检查后端 API
echo "📡 后端 API (端口 8000):"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "   ✅ 运行中"
    curl -s http://localhost:8000/api/health | python3 -m json.tool | grep -E "(status|message)" | head -10
else
    echo "   ❌ 未运行"
fi
echo ""

# 检查前端服务器
echo "🌐 前端服务器 (端口 8080):"
if curl -s http://localhost:8080/ > /dev/null 2>&1; then
    echo "   ✅ 运行中"
else
    echo "   ❌ 未运行"
fi
echo ""

# 检查 Redis
echo "💾 Redis:"
if redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ 运行中"
else
    echo "   ❌ 未运行"
fi
echo ""

# 检查 PostgreSQL
echo "🗄️  PostgreSQL:"
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "   ✅ 运行中"
else
    echo "   ❌ 未运行"
fi
echo ""

# 检查 Celery Worker
echo "⚙️  Celery Worker:"
if pgrep -f "celery.*worker" > /dev/null 2>&1; then
    echo "   ✅ 运行中 (PID: $(pgrep -f 'celery.*worker'))"
else
    echo "   ❌ 未运行"
fi
echo ""

# 检查 Celery Beat
echo "⏰ Celery Beat:"
if pgrep -f "celery.*beat" > /dev/null 2>&1; then
    echo "   ✅ 运行中 (PID: $(pgrep -f 'celery.*beat'))"
else
    echo "   ❌ 未运行"
fi
echo ""

echo "📍 访问地址："
echo "   - 前端查看界面: http://localhost:8080/index.html"
echo "   - 前端管理面板: http://localhost:8080/admin.html"
echo "   - 后端API文档: http://localhost:8000/docs"
echo "   - 健康检查: http://localhost:8000/api/health"
