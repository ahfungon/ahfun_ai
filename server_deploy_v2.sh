#!/bin/bash
set -e

echo "=========================================="
echo "Dual Agent Chat Platform 部署脚本 v2"
echo "=========================================="

# 1. 检查 Redis（手动启动）
echo ""
echo "[1/11] 检查 Redis 服务..."
if redis-cli ping > /dev/null 2>&1; then
    echo "Redis 已运行"
else
    echo "启动 Redis..."
    sudo /usr/bin/redis-server /etc/redis/redis.conf --daemonize yes
    sleep 2
    redis-cli ping
fi

# 2. 进入应用目录
echo ""
echo "[2/11] 进入应用目录..."
cd ~/dual-agent-chat

# 3. 创建虚拟环境
echo ""
echo "[3/11] 创建 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "Python 虚拟环境已激活"
echo "Python 路径: $(which python)"
echo "Python 版本: $(python --version)"

# 4. 安装 Python 依赖
echo ""
echo "[4/11] 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. 配置 PostgreSQL 数据库
echo ""
echo "[5/11] 配置 PostgreSQL 数据库..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS dual_agent_chat;"
sudo -u postgres psql -c "DROP USER IF EXISTS dual_agent_user;"
sudo -u postgres psql -c "CREATE USER dual_agent_user WITH PASSWORD 'dual_agent_pass';"
sudo -u postgres psql -c "CREATE DATABASE dual_agent_chat OWNER dual_agent_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dual_agent_chat TO dual_agent_user;"

# 6. 运行数据库迁移
echo ""
echo "[6/11] 运行数据库迁移..."
if [ -d "alembic" ]; then
    alembic upgrade head
    echo "数据库迁移完成"
else
    echo "警告: Alembic 未初始化"
fi

# 7. 导入测试数据
echo ""
echo "[7/11] 导入测试数据..."
if [ -f "dual_agent_chat_data.sql" ]; then
    PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -f dual_agent_chat_data.sql
    echo "测试数据导入完成"
else
    echo "警告: 未找到数据文件 dual_agent_chat_data.sql"
fi

# 8. 创建日志目录
echo ""
echo "[8/11] 创建日志目录..."
mkdir -p logs
chmod 755 logs

# 9. 创建 systemd 服务文件
echo ""
echo "[9/11] 创建 systemd 服务..."

# FastAPI 服务
sudo tee /etc/systemd/system/dual-agent-api.service > /dev/null <<EOF
[Unit]
Description=Dual Agent Chat API
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dual-agent-chat
Environment="PATH=/home/ubuntu/dual-agent-chat/venv/bin"
ExecStart=/home/ubuntu/dual-agent-chat/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/dual-agent-chat/logs/api.log
StandardError=append:/home/ubuntu/dual-agent-chat/logs/api.log

[Install]
WantedBy=multi-user.target
EOF

# Celery Worker 服务
sudo tee /etc/systemd/system/dual-agent-celery.service > /dev/null <<EOF
[Unit]
Description=Dual Agent Chat Celery Worker
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dual-agent-chat
Environment="PATH=/home/ubuntu/dual-agent-chat/venv/bin"
ExecStart=/home/ubuntu/dual-agent-chat/venv/bin/celery -A workers.celery_app worker --loglevel=info
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/dual-agent-chat/logs/worker.log
StandardError=append:/home/ubuntu/dual-agent-chat/logs/worker.log

[Install]
WantedBy=multi-user.target
EOF

# Celery Beat 服务
sudo tee /etc/systemd/system/dual-agent-celery-beat.service > /dev/null <<EOF
[Unit]
Description=Dual Agent Chat Celery Beat
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dual-agent-chat
Environment="PATH=/home/ubuntu/dual-agent-chat/venv/bin"
ExecStart=/home/ubuntu/dual-agent-chat/venv/bin/celery -A workers.celery_app beat --loglevel=info
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/dual-agent-chat/logs/beat.log
StandardError=append:/home/ubuntu/dual-agent-chat/logs/beat.log

[Install]
WantedBy=multi-user.target
EOF

# 10. 配置 Nginx
echo ""
echo "[10/11] 配置 Nginx..."
sudo tee /etc/nginx/sites-available/dual-agent-chat > /dev/null <<'NGINXEOF'
server {
    listen 8080;
    server_name _;

    client_max_body_size 10M;

    # 前端静态文件
    location / {
        root /home/ubuntu/dual-agent-chat/frontend;
        try_files $uri $uri/ /monitor.html;
        index monitor.html;
    }

    # 静态资源
    location /static/ {
        alias /home/ubuntu/dual-agent-chat/static/;
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
NGINXEOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/dual-agent-chat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# 11. 启动所有服务
echo ""
echo "[11/11] 启动所有服务..."
sudo systemctl daemon-reload

# 停止旧服务（如果存在）
sudo systemctl stop dual-agent-api || true
sudo systemctl stop dual-agent-celery || true
sudo systemctl stop dual-agent-celery-beat || true

# 启动新服务
sudo systemctl start dual-agent-api
sudo systemctl start dual-agent-celery
sudo systemctl start dual-agent-celery-beat

sudo systemctl enable dual-agent-api
sudo systemctl enable dual-agent-celery
sudo systemctl enable dual-agent-celery-beat

# 等待服务启动
sleep 5

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "服务状态："
echo ""
echo "--- FastAPI ---"
sudo systemctl status dual-agent-api --no-pager -l | head -15
echo ""
echo "--- Celery Worker ---"
sudo systemctl status dual-agent-celery --no-pager -l | head -15
echo ""
echo "--- Celery Beat ---"
sudo systemctl status dual-agent-celery-beat --no-pager -l | head -15
echo ""
echo "--- Nginx ---"
sudo systemctl status nginx --no-pager -l | head -15
echo ""
echo "--- Redis ---"
redis-cli ping

echo ""
echo "=========================================="
echo "访问地址："
echo "  前端监控: http://129.211.28.211:8080"
echo "  前端聊天: http://129.211.28.211:8080/index.html"
echo "  管理界面: http://129.211.28.211:8080/admin.html"
echo "  API 文档: http://129.211.28.211:8080/docs"
echo ""
echo "请确保防火墙已开放 8080 端口！"
echo "=========================================="
