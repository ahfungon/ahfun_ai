#!/bin/bash

# 快速更新脚本 - 只同步代码文件并重启服务
# 用法: ./quick_update.sh [文件路径...]
# 示例: ./quick_update.sh services/summary_service.py

set -e

SERVER="ubuntu@129.211.28.211"
KEY="~/.ssh/mingkuan.pem"
REMOTE_DIR="~/dual-agent-chat"

echo "=========================================="
echo "快速更新到服务器"
echo "=========================================="

# 如果指定了文件，只同步这些文件
if [ $# -gt 0 ]; then
    echo ""
    echo "📦 同步指定文件..."
    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "  ✓ $file"
            rsync -avz -e "ssh -i $KEY" "$file" "$SERVER:$REMOTE_DIR/$file"
        else
            echo "  ✗ 文件不存在: $file"
        fi
    done
else
    # 否则同步所有 Python 代码文件
    echo ""
    echo "📦 同步所有代码文件..."
    rsync -avz -e "ssh -i $KEY" \
        --include='*.py' \
        --include='*/' \
        --exclude='*' \
        --exclude='.git/' \
        --exclude='venv/' \
        --exclude='__pycache__/' \
        --exclude='.pytest_cache/' \
        --exclude='.hypothesis/' \
        ./ "$SERVER:$REMOTE_DIR/"
fi

echo ""
echo "🔄 重启服务..."
ssh -i $KEY $SERVER << 'EOF'
cd ~/dual-agent-chat

# 只重启需要的服务
echo "  重启 API 服务..."
sudo systemctl restart dual-agent-api

echo "  重启 Celery Worker..."
sudo systemctl restart dual-agent-celery

echo "✓ 服务已重启"
EOF

echo ""
echo "=========================================="
echo "✅ 快速更新完成！"
echo "=========================================="
echo ""
echo "验证服务状态："
echo "  ssh -i $KEY $SERVER 'systemctl status dual-agent-api dual-agent-celery'"
echo ""
echo "查看日志："
echo "  ssh -i $KEY $SERVER 'journalctl -u dual-agent-api -f'"
echo "  ssh -i $KEY $SERVER 'journalctl -u dual-agent-celery -f'"
echo ""
