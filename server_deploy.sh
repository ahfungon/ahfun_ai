#!/bin/bash
set -e

echo "=========================================="
echo "Dual Agent Chat Platform 部署脚本"
echo "=========================================="

# 1. 安装必要的软件
echo ""
echo "[1/12] 安装 Redis 和 Nginx..."
sudo apt install -y redis-server nginx python3-pip python3-venv

# 2. 启动 Redis
echo ""
echo "[2/12] 启动 Redis 服务..."
sudo systemctl start redis-server
sudo systemctl enable redis-server
redis-cli ping

# 3. 进入应用目录
echo ""
echo "[3/12] 进入应用目录..."
cd ~/dual-agent-chat

# 4. 创建虚拟环境
echo ""
echo "[4/12] 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

echo "Python 虚拟环境已激活"
echo "Python 路径: $(which python)"
echo "Python 版本: $(python --version)"

# 5. 安装 Python 依赖
echo ""
echo "[5/12] 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. 配置 PostgreSQL 数据库
echo ""
echo "[6/12] 配置 PostgreSQL 数据库..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS dual_agent_chat;"
sudo -u postgres psql -c "DROP USER IF EXISTS dual_agent_user;"
sudo -u postgres psql -c "CREATE USER dual_agent_user WITH PASSWORD 'dual_agent_pass';"
sudo -u postgres psql -c "CREATE DATABASE dual_agent_chat OWNER dual_agent_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dual_agent_chat TO dual_agent_user;"

# 7. 运行数据库迁移
echo ""
echo "[7/12] 运行数据库迁移..."
if [ -d "alembic" ]; then
    alembic upgrade head
    echo "数据库迁移完成"
else
    echo "警告: Alembic 未初始化"
fi

# 8. 导入测试数据
echo ""
echo "[8/12] 导入测试数据..."
if [ -f "dual_agent_chat_data.sql" ]; then
    PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -f dual_agent_chat_data.sql
    echo "测试数据导入完成"
else
    echo "警告: 未找到数据文件 dual_agent_chat_data.sql"
fi

# 9. 创建日志目录
echo ""
echo "[9/12] 创建日志目录..."
mkdir -p logs
chmod 755 logs

# 10. 创建 systemd 服务文件
echo ""
echo "[10/12] 创建 systemd 服务..."

# FastAPI 服务
sudo tee /etc/systemd/system/dual-agent-api.service > /dev/null <<EOF
[Unit]
Description=Dual Agent Chat API
After=network.target postgresql.service redis.service

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
After=network.target redis.service

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
After=network.target redis.service

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

# 11. 配置 Nginx
echo ""
echo "[11/12] 配置 Nginx..."
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

# 12. 启动所有服务
echo ""
echo "[12/12] 启动所有服务..."
sudo systemctl daemon-reload

sudo systemctl restart dual-agent-api
sudo systemctl restart dual-agent-celery
sudo systemctl restart dual-agent-celery-beat

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
sudo systemctl status redis-server --no-pager -l | head -15

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
