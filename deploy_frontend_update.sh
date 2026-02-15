#!/bin/bash
set -e

echo "=========================================="
echo "前端更新部署脚本 - 明宽服务器"
echo "=========================================="

# 服务器配置
SERVER_USER="ubuntu"
SERVER_HOST="129.211.28.211"
SERVER_PATH="/home/ubuntu/dual-agent-chat"
SSH_KEY="$HOME/.ssh/mingkuan.pem"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${YELLOW}准备部署新版前端到明宽服务器...${NC}"
echo "服务器: $SERVER_HOST"
echo "路径: $SERVER_PATH"
echo "密钥: $SSH_KEY"
echo ""

# 检查密钥文件
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}✗ SSH 密钥文件不存在: $SSH_KEY${NC}"
    exit 1
fi

# 1. 检查 SSH 连接
echo -e "${YELLOW}[1/6] 检查 SSH 连接...${NC}"
if ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "echo 'SSH 连接成功'" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH 连接正常${NC}"
else
    echo -e "${RED}✗ SSH 连接失败${NC}"
    echo "请检查："
    echo "  1. 服务器地址是否正确"
    echo "  2. SSH 密钥权限是否正确 (chmod 400 $SSH_KEY)"
    echo "  3. 网络连接是否正常"
    exit 1
fi

# 2. 备份服务器上的旧版本
echo ""
echo -e "${YELLOW}[2/6] 备份服务器上的旧版本...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd ~/dual-agent-chat/frontend
mkdir -p backup_$(date +%Y%m%d_%H%M%S)
if [ -f "index.html" ]; then
    cp index.html backup_$(date +%Y%m%d_%H%M%S)/
    echo "✓ 已备份 index.html"
fi
if [ -f "monitor.html" ]; then
    cp monitor.html backup_$(date +%Y%m%d_%H%M%S)/
    echo "✓ 已备份 monitor.html"
fi
ENDSSH
echo -e "${GREEN}✓ 服务器旧版本已备份${NC}"

# 3. 上传新版前端文件
echo ""
echo -e "${YELLOW}[3/6] 上传新版前端文件...${NC}"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no frontend/index.html $SERVER_USER@$SERVER_HOST:$SERVER_PATH/frontend/index.html
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no frontend/monitor.html $SERVER_USER@$SERVER_HOST:$SERVER_PATH/frontend/monitor.html
echo -e "${GREEN}✓ 前端文件上传完成${NC}"

# 4. 验证文件
echo ""
echo -e "${YELLOW}[4/6] 验证上传的文件...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd ~/dual-agent-chat/frontend
echo "文件大小："
ls -lh index.html monitor.html | awk '{print "  " $9 ": " $5}'
echo ""
echo "检查主题切换功能："
if grep -q "toggleTheme" index.html; then
    echo "  ✓ index.html 包含主题切换功能"
else
    echo "  ✗ index.html 缺少主题切换功能"
fi
if grep -q "toggleTheme" monitor.html; then
    echo "  ✓ monitor.html 包含主题切换功能"
else
    echo "  ✗ monitor.html 缺少主题切换功能"
fi
ENDSSH
echo -e "${GREEN}✓ 文件验证完成${NC}"

# 5. 重启 Nginx
echo ""
echo -e "${YELLOW}[5/6] 重启 Nginx...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST << 'ENDSSH'
sudo systemctl reload nginx
if sudo systemctl is-active --quiet nginx; then
    echo "✓ Nginx 重启成功"
else
    echo "✗ Nginx 重启失败"
    exit 1
fi
ENDSSH
echo -e "${GREEN}✓ Nginx 已重启${NC}"

# 6. 验证部署
echo ""
echo -e "${YELLOW}[6/6] 验证部署...${NC}"
echo "检查页面访问："
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$SERVER_HOST:8080)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "  ${GREEN}✓ 监控页面 (/) - HTTP $HTTP_CODE${NC}"
else
    echo -e "  ${RED}✗ 监控页面 (/) - HTTP $HTTP_CODE${NC}"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$SERVER_HOST:8080/index.html)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "  ${GREEN}✓ 聊天页面 (/index.html) - HTTP $HTTP_CODE${NC}"
else
    echo -e "  ${RED}✗ 聊天页面 (/index.html) - HTTP $HTTP_CODE${NC}"
fi

echo ""
echo "检查主题切换功能："
if curl -s http://$SERVER_HOST:8080 | grep -q "toggleTheme"; then
    echo -e "  ${GREEN}✓ 主题切换功能已部署${NC}"
else
    echo -e "  ${RED}✗ 主题切换功能未检测到${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "访问地址："
echo "  🌐 监控界面: http://$SERVER_HOST:8080"
echo "  💬 聊天界面: http://$SERVER_HOST:8080/index.html"
echo "  🔧 管理后台: http://$SERVER_HOST:8080/admin.html"
echo ""
echo "新功能："
echo "  ✨ AI 科技风格设计"
echo "  🌓 深色/浅色主题切换"
echo "  💎 毛玻璃导航栏"
echo "  ⚡ 平滑动画效果"
echo ""
echo "备份位置："
echo "  服务器: $SERVER_PATH/frontend/backup_$(date +%Y%m%d)_*/"
echo ""
echo "=========================================="
