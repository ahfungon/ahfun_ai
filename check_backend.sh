#!/bin/bash

echo "=========================================="
echo "后端服务状态检查"
echo "=========================================="

# 1. 检查进程
echo -e "\n1. 检查后端进程:"
if ps aux | grep "uvicorn main:app" | grep -v grep > /dev/null; then
    echo "✅ 后端进程运行中"
    ps aux | grep "uvicorn main:app" | grep -v grep | head -3
else
    echo "❌ 后端进程未运行"
    echo "   启动命令: bash start_backend.sh"
fi

# 2. 检查端口
echo -e "\n2. 检查端口 8080:"
if lsof -i :8080 > /dev/null 2>&1; then
    echo "✅ 端口 8080 已被占用"
    lsof -i :8080 | head -5
else
    echo "❌ 端口 8080 未被占用"
fi

# 3. 检查健康状态
echo -e "\n3. 检查健康状态:"
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "✅ 健康检查通过"
    curl -s http://localhost:8080/api/health | python -m json.tool 2>/dev/null | head -15
else
    echo "❌ 健康检查失败"
    echo "   后端服务可能未运行或无法访问"
fi

# 4. 检查 Worker
echo -e "\n4. 检查 Worker 状态:"
if curl -s http://localhost:8080/api/admin/worker/status > /dev/null 2>&1; then
    echo "✅ Worker 状态检查通过"
    curl -s http://localhost:8080/api/admin/worker/status | python -m json.tool 2>/dev/null
else
    echo "❌ Worker 状态检查失败"
fi

# 5. 检查最新日志
echo -e "\n5. 最新日志 (最后 10 行):"
if [ -f logs/api.log ]; then
    tail -10 logs/api.log
else
    echo "❌ 日志文件不存在"
fi

echo -e "\n=========================================="
echo "检查完成"
echo "=========================================="

# 返回状态码
if ps aux | grep "uvicorn main:app" | grep -v grep > /dev/null && \
   curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "✅ 后端服务运行正常"
    exit 0
else
    echo "❌ 后端服务异常"
    exit 1
fi
