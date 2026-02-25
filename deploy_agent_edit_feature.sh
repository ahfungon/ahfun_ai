#!/bin/bash
# 部署智能体编辑功能到生产服务器

set -e

echo "=== 部署智能体编辑功能 ==="
echo ""

# 服务器信息
SERVER="ubuntu@129.211.28.211"
APP_DIR="/home/ubuntu/dual-agent-chat"

echo "1. 连接到服务器并更新代码..."
ssh -i ~/.ssh/mingkuan.pem $SERVER << 'ENDSSH'
cd /home/ubuntu/dual-agent-chat

# 拉取最新代码
echo "拉取最新代码..."
git pull origin main

# 执行数据库迁移
echo ""
echo "执行数据库迁移..."
psql postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat -f migrations/add_agent_system_prompt.sql

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
echo "  管理后台: http://129.211.28.211:8080/admin.html"
echo ""
echo "测试步骤："
echo "  1. 在模拟器页面点击'添加智能体'"
echo "  2. 填写名称和系统提示词"
echo "  3. 注册后，点击智能体卡片上的'编辑'按钮"
echo "  4. 修改名称或系统提示词"
echo "  5. 保存并验证修改是否生效"
