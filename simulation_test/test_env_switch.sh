#!/bin/bash

# 测试环境切换功能

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "测试智能体环境切换功能"
echo "=========================================="
echo ""

# 测试1：显示帮助信息
echo -e "${YELLOW}[测试1] 显示帮助信息${NC}"
python3 simulation_test/autonomous_agent.py --help
echo ""

# 测试2：测试本地环境参数
echo -e "${YELLOW}[测试2] 测试本地环境参数${NC}"
echo "命令: python3 simulation_test/autonomous_agent.py --agent alice --env local"
echo "预期: 显示连接到本地服务"
echo ""
timeout 3 python3 simulation_test/autonomous_agent.py --agent alice --env local 2>&1 | head -20 || true
echo ""

# 测试3：测试服务器环境参数
echo -e "${YELLOW}[测试3] 测试服务器环境参数${NC}"
echo "命令: python3 simulation_test/autonomous_agent.py --agent alice --env server"
echo "预期: 显示连接到明宽服务器"
echo ""
timeout 3 python3 simulation_test/autonomous_agent.py --agent alice --env server 2>&1 | head -20 || true
echo ""

# 测试4：测试启动脚本帮助
echo -e "${YELLOW}[测试4] 测试启动脚本${NC}"
echo "命令: ./simulation_test/start_agents.sh --env local"
echo "预期: 显示本地环境启动信息"
echo ""
echo "（跳过实际启动，仅显示用法）"
echo "用法: ./simulation_test/start_agents.sh [--env local|server]"
echo ""

echo "=========================================="
echo -e "${GREEN}✓ 环境切换功能测试完成${NC}"
echo "=========================================="
echo ""
echo "使用方法："
echo "  本地测试: python3 simulation_test/autonomous_agent.py --agent alice --env local"
echo "  服务器测试: python3 simulation_test/autonomous_agent.py --agent alice --env server"
echo ""
echo "批量启动："
echo "  本地: ./simulation_test/start_agents.sh --env local"
echo "  服务器: ./simulation_test/start_agents.sh --env server"
echo ""
