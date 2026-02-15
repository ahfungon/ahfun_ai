#!/bin/bash

# 停止所有智能体进程的脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "停止智能体进程"
echo "=========================================="
echo ""

# 检查是否有运行中的智能体进程
RUNNING_AGENTS=$(ps aux | grep -E '(autonomous_agent|simulate|enhanced_simulator)' | grep -v grep | wc -l)

if [ "$RUNNING_AGENTS" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  没有发现运行中的智能体进程${NC}"
    exit 0
fi

echo -e "${YELLOW}发现 $RUNNING_AGENTS 个运行中的智能体进程${NC}"
echo ""

# 显示进程信息
echo "运行中的进程："
ps aux | grep -E '(autonomous_agent|simulate|enhanced_simulator)' | grep -v grep | awk '{print "  PID: " $2 " - " $11 " " $12 " " $13 " " $14}'
echo ""

# 停止进程
echo -e "${YELLOW}正在停止进程...${NC}"
pkill -9 -f "autonomous_agent.py" 2>/dev/null || true
pkill -9 -f "simulate.*\.py" 2>/dev/null || true
pkill -9 -f "enhanced_simulator.py" 2>/dev/null || true

# 等待进程完全停止
sleep 1

# 验证是否已停止
REMAINING=$(ps aux | grep -E '(autonomous_agent|simulate|enhanced_simulator)' | grep -v grep | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo -e "${GREEN}✓ 所有智能体进程已成功停止${NC}"
else
    echo -e "${RED}⚠️  仍有 $REMAINING 个进程未停止，请手动检查${NC}"
    ps aux | grep -E '(autonomous_agent|simulate|enhanced_simulator)' | grep -v grep
    exit 1
fi

echo ""
echo "=========================================="
