#!/bin/bash
set -e

echo "=========================================="
echo "开始部署 Dual Agent Chat Platform"
echo "=========================================="

# 1. 安装必要的软件
echo ""
echo "[1/10] 安装 Redis 和 Nginx..."
sudo apt install -y redis-server nginx python3-pip python3-venv

# 2. 启动 Redis
echo ""
echo "[2/10] 启动 Redis 服务..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 3. 创建应用目录
echo ""
echo "[3/10] 创建应用目录..."
mkdir -p ~/dual-agent-chat
cd ~/dual-agent-chat

# 4. 创建虚拟环境
echo ""
echo "[4/10] 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

echo "Python 虚拟环境已激活"
echo "Python 路径: $(which python)"
echo "Python 版本: $(python --version)"

# 5. 等待文件上传
echo ""
echo "[5/10] 等待代码文件上传..."
echo "请在本地执行以下命令上传代码："
echo "rsync -avz --exclude 'venv' --exclude '.git' --exclude '__pycache__' --exclude '.hypothesis' --exclude '*.pyc' -e 'ssh -i ~/.ssh/mingkuan.pem' ./ ubuntu@129.211.28.211:~/dual-agent-chat/"
echo ""
read -p "文件上传完成后，按回车继续..."

# 6. 安装 Python 依赖
echo ""
echo "[6/10] 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 7. 配置数据库
echo ""
echo "[7/10] 配置 PostgreSQL 数据库..."
sudo -u postgres psql -c "CREATE DATABASE dual_agent_chat;" || echo "数据库已存在"
sudo -u postgres psql -c "CREATE USER dual_agent_user WITH PASSWORD 'dual_agent_pass';" || echo "用户已存在"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dual_agent_chat TO dual_agent_user;"
sudo -u postgres psql -c "ALTER DATABASE dual_agent_chat OWNER TO dual_agent_user;"

# 8. 运行数据库迁移
echo ""
echo "[8/10] 运行数据库迁移..."
if [ -d "alembic" ]; then
    alembic upgrade head
else
    echo "Alembic 未初始化，跳过迁移"
fi

# 9. 创建 systemd 服务文件
echo ""
echo "[9/10] 创建 systemd 服务..."

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

[Install]
WantedBy=multi-user.target
EOF

# 10. 配置 Nginx
echo ""
echo "[10/10] 配置 Nginx..."
sudo tee /etc/nginx/sites-available/dual-agent-chat > /dev/null <<'EOF'
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
EOF

sudo ln -sf /etc/nginx/sites-available/dual-agent-chat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# 重新加载 systemd 并启动服务
echo ""
echo "重新加载 systemd 配置..."
sudo systemctl daemon-reload

echo ""
echo "启动所有服务..."
sudo systemctl start dual-agent-api
sudo systemctl start dual-agent-celery
sudo systemctl start dual-agent-celery-beat

sudo systemctl enable dual-agent-api
sudo systemctl enable dual-agent-celery
sudo systemctl enable dual-agent-celery-beat

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "服务状态："
sudo systemctl status dual-agent-api --no-pager -l
sudo systemctl status dual-agent-celery --no-pager -l
sudo systemctl status dual-agent-celery-beat --no-pager -l
sudo systemctl status nginx --no-pager -l

echo ""
echo "访问地址："
echo "  前端: http://129.211.28.211:8080"
echo "  API 文档: http://129.211.28.211:8080/docs"
echo ""
echo "请确保防火墙已开放 8080 端口"
