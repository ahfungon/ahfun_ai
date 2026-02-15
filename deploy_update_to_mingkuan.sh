#!/bin/bash
set -e

# 明宽服务器配置
SERVER_IP="129.211.28.211"
SERVER_USER="ubuntu"
SSH_KEY="~/.ssh/mingkuan.pem"
REMOTE_DIR="~/dual-agent-chat"

echo "=========================================="
echo "更新代码到明宽服务器（保留现有数据）"
echo "服务器: ${SERVER_USER}@${SERVER_IP}"
echo "=========================================="

# 1. 同步代码到服务器
echo ""
echo "[1/4] 同步代码到服务器..."
rsync -avz --progress \
    --exclude 'venv' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '.hypothesis' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'logs' \
    --exclude '.env' \
    --exclude 'simulation_test/.agent_state' \
    --exclude '*.sql' \
    -e "ssh -i ${SSH_KEY}" \
    ./ ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/

echo "✓ 代码同步完成"

# 2. 检查并更新 .env 文件
echo ""
echo "[2/4] 检查 .env 配置..."
if [ -f ".env" ]; then
    echo "本地 .env 文件存在，是否要更新到服务器？"
    echo "注意：这会覆盖服务器上的 .env 文件"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        scp -i ${SSH_KEY} .env ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/.env
        echo "✓ .env 文件已更新"
    else
        echo "跳过 .env 文件更新"
    fi
else
    echo "⚠️  本地 .env 文件不存在，请确保服务器上已配置"
fi

# 3. 在服务器上执行更新
echo ""
echo "[3/4] 在服务器上执行更新..."
ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

echo "=========================================="
echo "服务器端更新开始"
echo "=========================================="

cd ~/dual-agent-chat

# 检查 .env 文件
echo ""
echo "检查 .env 配置..."
if [ ! -f ".env" ]; then
    echo "❌ 错误: .env 文件不存在！"
    echo "请先创建 .env 文件并配置必要的环境变量"
    exit 1
fi

# 检查 DeepSeek API Key
if ! grep -q "DEEPSEEK_API_KEY=sk-" .env; then
    echo "⚠️  警告: DeepSeek API Key 可能未配置"
fi

echo "✓ .env 文件存在"

# 激活虚拟环境
echo ""
echo "激活 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate

# 安装/更新依赖
echo ""
echo "更新 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✓ 依赖更新完成"

# 检查 Redis
echo ""
echo "检查 Redis 服务..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "启动 Redis..."
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    sleep 2
fi
redis-cli ping
echo "✓ Redis 运行正常"

# 检查 PostgreSQL
echo ""
echo "检查 PostgreSQL 服务..."
if ! sudo -u postgres psql -c "SELECT 1" > /dev/null 2>&1; then
    echo "启动 PostgreSQL..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    sleep 2
fi
echo "✓ PostgreSQL 运行正常"

# 备份当前数据库
echo ""
echo "备份当前数据库..."
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
PGPASSWORD='dual_agent_pass' pg_dump -h localhost -U dual_agent_user -d dual_agent_chat \
    --clean --if-exists \
    -f "$BACKUP_FILE"
echo "✓ 数据库已备份到: $BACKUP_FILE"

# 创建日志目录
mkdir -p logs
chmod 755 logs

# 停止服务
echo ""
echo "停止服务..."
sudo systemctl stop dual-agent-api || true
sudo systemctl stop dual-agent-celery || true
sudo systemctl stop dual-agent-celery-beat || true
sleep 2
echo "✓ 服务已停止"

# 启动服务
echo ""
echo "启动服务..."
sudo systemctl start dual-agent-api
sudo systemctl start dual-agent-celery
sudo systemctl start dual-agent-celery-beat
sudo systemctl restart nginx

# 等待服务启动
echo "等待服务启动..."
sleep 5

echo ""
echo "=========================================="
echo "服务器端更新完成"
echo "=========================================="

# 检查服务状态
echo ""
echo "服务状态："
echo ""
echo "--- FastAPI ---"
sudo systemctl status dual-agent-api --no-pager -l | head -10
echo ""
echo "--- Celery Worker ---"
sudo systemctl status dual-agent-celery --no-pager -l | head -10
echo ""
echo "--- Celery Beat ---"
sudo systemctl status dual-agent-celery-beat --no-pager -l | head -10
echo ""
echo "--- Nginx ---"
sudo systemctl status nginx --no-pager -l | head -5

ENDSSH

# 4. 验证部署
echo ""
echo "[4/4] 验证部署..."
echo ""
echo "等待服务完全启动..."
sleep 3

echo "检查 API 健康状态..."
if curl -s http://${SERVER_IP}:8080/api/health | grep -q "healthy"; then
    echo "✓ API 服务正常"
else
    echo "⚠️  API 服务可能需要更多时间启动，请稍后检查"
fi

echo ""
echo "检查前端页面..."
if curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8080/monitor.html | grep -q "200"; then
    echo "✓ 监控页面可访问"
else
    echo "⚠️  监控页面访问异常"
fi

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  🌐 监控页面: http://${SERVER_IP}:8080/monitor.html"
echo "  💬 聊天页面: http://${SERVER_IP}:8080/index.html"
echo "  🔧 管理页面: http://${SERVER_IP}:8080/admin.html"
echo "  📚 API 文档: http://${SERVER_IP}:8080/docs"
echo "  📖 智能体指南: http://${SERVER_IP}:8080/ai-agent-guide.html"
echo ""
echo "查看日志："
echo "  ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} 'tail -f ~/dual-agent-chat/logs/api.log'"
echo "  ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} 'tail -f ~/dual-agent-chat/logs/worker.log'"
echo "  ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} 'tail -f ~/dual-agent-chat/logs/beat.log'"
echo ""
echo "数据库备份："
echo "  服务器上已创建数据库备份文件（backup_*.sql）"
echo ""
echo "=========================================="
