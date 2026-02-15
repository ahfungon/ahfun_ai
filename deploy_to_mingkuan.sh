#!/bin/bash
set -e

# 明宽服务器配置
SERVER_IP="129.211.28.211"
SERVER_USER="ubuntu"
SSH_KEY="~/.ssh/mingkuan.pem"
REMOTE_DIR="~/dual-agent-chat"

echo "=========================================="
echo "部署到明宽服务器"
echo "服务器: ${SERVER_USER}@${SERVER_IP}"
echo "=========================================="

# 1. 导出本地数据库
echo ""
echo "[1/5] 导出本地数据库..."
if command -v pg_dump &> /dev/null; then
    PGPASSWORD='dual_agent_pass' pg_dump -h localhost -U dual_agent_user -d dual_agent_chat \
        --clean --if-exists \
        -f dual_agent_chat_data.sql
    echo "数据库导出完成: dual_agent_chat_data.sql"
else
    echo "警告: pg_dump 未安装，跳过数据库导出"
fi

# 2. 同步代码到服务器
echo ""
echo "[2/5] 同步代码到服务器..."
rsync -avz --progress \
    --exclude 'venv' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '.hypothesis' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'logs' \
    --exclude '.env' \
    -e "ssh -i ${SSH_KEY}" \
    ./ ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/

echo "代码同步完成"

# 3. 复制环境配置
echo ""
echo "[3/5] 复制环境配置..."
if [ -f ".env" ]; then
    scp -i ${SSH_KEY} .env ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/.env
    echo ".env 文件已复制"
else
    echo "警告: .env 文件不存在，请手动配置"
fi

# 4. 在服务器上执行部署
echo ""
echo "[4/5] 在服务器上执行部署..."
ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

echo "=========================================="
echo "服务器端部署开始"
echo "=========================================="

cd ~/dual-agent-chat

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

# 激活虚拟环境
echo ""
echo "激活 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 安装/更新依赖
echo ""
echo "安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 配置数据库
echo ""
echo "配置 PostgreSQL 数据库..."
sudo -u postgres psql << 'EOSQL'
-- 断开所有连接
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'dual_agent_chat' AND pid <> pg_backend_pid();

-- 重建数据库
DROP DATABASE IF EXISTS dual_agent_chat;
DROP USER IF EXISTS dual_agent_user;
CREATE USER dual_agent_user WITH PASSWORD 'dual_agent_pass';
CREATE DATABASE dual_agent_chat OWNER dual_agent_user;
GRANT ALL PRIVILEGES ON DATABASE dual_agent_chat TO dual_agent_user;
EOSQL

echo "数据库配置完成"

# 导入数据
echo ""
echo "导入数据库..."
if [ -f "dual_agent_chat_data.sql" ]; then
    PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -f dual_agent_chat_data.sql
    echo "数据导入完成"
else
    echo "警告: 未找到数据文件，运行迁移创建空数据库"
    if [ -d "alembic" ]; then
        alembic upgrade head
    fi
fi

# 创建日志目录
mkdir -p logs
chmod 755 logs

# 重启服务
echo ""
echo "重启服务..."
sudo systemctl restart dual-agent-api
sudo systemctl restart dual-agent-celery
sudo systemctl restart dual-agent-celery-beat
sudo systemctl restart nginx

# 等待服务启动
sleep 5

echo ""
echo "=========================================="
echo "服务器端部署完成"
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
sudo systemctl status nginx --no-pager -l | head -10

ENDSSH

# 5. 验证部署
echo ""
echo "[5/5] 验证部署..."
echo ""
echo "检查 API 健康状态..."
if curl -s http://${SERVER_IP}:8080/api/health | grep -q "healthy"; then
    echo "✓ API 服务正常"
else
    echo "✗ API 服务异常，请检查日志"
fi

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  监控页面: http://${SERVER_IP}:8080/monitor.html"
echo "  聊天页面: http://${SERVER_IP}:8080/index.html"
echo "  管理页面: http://${SERVER_IP}:8080/admin.html"
echo "  历史记录: http://${SERVER_IP}:8080/history.html"
echo "  API 文档: http://${SERVER_IP}:8080/docs"
echo ""
echo "查看日志："
echo "  ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} 'tail -f ~/dual-agent-chat/logs/api.log'"
echo "  ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} 'tail -f ~/dual-agent-chat/logs/worker.log'"
echo ""
echo "=========================================="
