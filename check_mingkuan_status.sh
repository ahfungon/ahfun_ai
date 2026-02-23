#!/bin/bash

# 明宽服务器配置
SERVER_IP="129.211.28.211"
SERVER_USER="ubuntu"
SSH_KEY="~/.ssh/mingkuan.pem"

echo "=========================================="
echo "检查明宽服务器状态"
echo "=========================================="

# 检查 API 健康状态
echo ""
echo "[1/4] 检查 API 健康状态..."
if curl -s http://${SERVER_IP}:8080/api/health | jq . 2>/dev/null; then
    echo "✓ API 服务正常"
else
    echo "✗ API 服务异常"
fi

# 检查话题列表
echo ""
echo "[2/4] 检查话题列表..."
curl -s http://${SERVER_IP}:8080/api/topics | jq '.topics | length' 2>/dev/null | \
    xargs -I {} echo "当前话题数: {}"

# 检查服务状态
echo ""
echo "[3/4] 检查服务状态..."
ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
echo ""
echo "--- 服务运行状态 ---"
systemctl is-active dual-agent-api && echo "✓ FastAPI: 运行中" || echo "✗ FastAPI: 已停止"
systemctl is-active dual-agent-celery && echo "✓ Celery Worker: 运行中" || echo "✗ Celery Worker: 已停止"
systemctl is-active dual-agent-celery-beat && echo "✓ Celery Beat: 运行中" || echo "✗ Celery Beat: 已停止"
systemctl is-active nginx && echo "✓ Nginx: 运行中" || echo "✗ Nginx: 已停止"
redis-cli ping > /dev/null 2>&1 && echo "✓ Redis: 运行中" || echo "✗ Redis: 已停止"

echo ""
echo "--- 数据库连接 ---"
PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -c "SELECT COUNT(*) as topic_count FROM topics;" 2>/dev/null || echo "✗ 数据库连接失败"

echo ""
echo "--- 最近日志 (最后 5 行) ---"
echo "API 日志:"
tail -5 ~/dual-agent-chat/logs/api.log 2>/dev/null || echo "无日志"
echo ""
echo "Worker 日志:"
tail -5 ~/dual-agent-chat/logs/worker.log 2>/dev/null || echo "无日志"
ENDSSH

# 检查网页可访问性
echo ""
echo "[4/4] 检查网页可访问性..."
for page in "monitor.html" "index.html" "admin.html" "history.html"; do
    if curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8080/${page} | grep -q "200"; then
        echo "✓ ${page}: 可访问"
    else
        echo "✗ ${page}: 不可访问"
    fi
done

echo ""
echo "=========================================="
echo "状态检查完成"
echo "=========================================="
