#!/bin/bash
# 通过直接拷贝文件部署智能体编辑功能到生产服务器

set -e

echo "=== 部署智能体编辑功能（文件拷贝方式） ==="
echo ""

# 服务器信息
SERVER="ubuntu@129.211.28.211"
APP_DIR="/home/ubuntu/dual-agent-chat"

echo "1. 拷贝修改的文件到服务器..."
echo "  - api/routes.py"
scp -i ~/.ssh/mingkuan.pem api/routes.py $SERVER:$APP_DIR/api/

echo "  - frontend/simulator.html"
scp -i ~/.ssh/mingkuan.pem frontend/simulator.html $SERVER:$APP_DIR/frontend/

echo "  - models/models.py"
scp -i ~/.ssh/mingkuan.pem models/models.py $SERVER:$APP_DIR/models/

echo "  - migrations/add_agent_system_prompt.sql"
scp -i ~/.ssh/mingkuan.pem migrations/add_agent_system_prompt.sql $SERVER:$APP_DIR/migrations/

echo ""
echo "2. 执行数据库迁移并重启服务..."
ssh -i ~/.ssh/mingkuan.pem $SERVER << 'ENDSSH'
cd /home/ubuntu/dual-agent-chat

# 执行数据库迁移
echo "执行数据库迁移..."
sudo -u postgres psql -d dual_agent_chat -f migrations/add_agent_system_prompt.sql

# 重启服务
echo ""
echo "重启后端服务..."
sudo systemctl restart dual-agent-api

# 等待服务启动
echo "等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "检查服务状态..."
sudo systemctl status dual-agent-api --no-pager | head -15

ENDSSH

echo ""
echo "=== 部署完成 ==="
echo ""
echo "请访问以下地址测试："
echo "  模拟器页面: http://129.211.28.211:8080/simulator.html"
echo ""
echo "测试步骤："
echo "  1. 在模拟器页面点击'添加智能体'"
echo "  2. 填写名称和系统提示词（例如：'你是一个友好的助手，说话风格幽默风趣。'）"
echo "  3. 注册后，点击智能体卡片上的'编辑'按钮"
echo "  4. 修改名称或系统提示词"
echo "  5. 保存并验证修改是否生效"
