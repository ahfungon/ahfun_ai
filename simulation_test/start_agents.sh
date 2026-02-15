#!/bin/bash

# 自主智能体启动脚本
# 支持本地和服务器环境切换

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认环境
ENV="local"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: $0 [--env local|server]"
            exit 1
            ;;
    esac
done

# 验证环境参数
if [[ "$ENV" != "local" && "$ENV" != "server" ]]; then
    echo -e "${YELLOW}⚠️  无效的环境参数: $ENV${NC}"
    echo "请使用: local 或 server"
    exit 1
fi

# 显示环境信息
echo "=========================================="
echo "自主智能体启动"
if [[ "$ENV" == "server" ]]; then
    echo -e "${BLUE}🌐 目标环境: 明宽服务器 (129.211.28.211:8080)${NC}"
else
    echo -e "${GREEN}🏠 目标环境: 本地服务 (localhost:8000)${NC}"
fi
echo "=========================================="
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
pip install -q -r requirements.txt

# 创建日志目录
mkdir -p simulation_test/logs

# 启动智能体
echo ""
echo -e "${GREEN}启动智能体...${NC}"
echo ""

# 使用 tmux 或 screen 启动多个智能体（如果可用）
if command -v tmux &> /dev/null; then
    echo "使用 tmux 启动智能体..."
    
    # 创建新会话
    tmux new-session -d -s agents
    
    # 启动 Alice
    tmux send-keys -t agents "source venv/bin/activate" C-m
    tmux send-keys -t agents "python3 simulation_test/autonomous_agent.py --agent alice --env $ENV" C-m
    
    # 创建新窗口启动 Bob
    tmux new-window -t agents
    tmux send-keys -t agents "source venv/bin/activate" C-m
    tmux send-keys -t agents "python3 simulation_test/autonomous_agent.py --agent bob --env $ENV" C-m
    
    echo ""
    echo -e "${GREEN}✓ 智能体已在 tmux 会话中启动${NC}"
    echo ""
    echo "查看智能体："
    echo "  tmux attach -t agents    # 连接到会话"
    echo "  Ctrl+B, N                # 切换窗口"
    echo "  Ctrl+B, D                # 分离会话"
    echo ""
    echo "停止智能体："
    echo "  tmux kill-session -t agents"
    
else
    echo -e "${YELLOW}⚠️  未安装 tmux，使用后台进程启动${NC}"
    echo ""
    
    # 后台启动
    nohup python3 simulation_test/autonomous_agent.py --agent alice --env $ENV > simulation_test/logs/alice.log 2>&1 &
    ALICE_PID=$!
    echo -e "${GREEN}✓ Alice 已启动 (PID: $ALICE_PID)${NC}"
    
    nohup python3 simulation_test/autonomous_agent.py --agent bob --env $ENV > simulation_test/logs/bob.log 2>&1 &
    BOB_PID=$!
    echo -e "${GREEN}✓ Bob 已启动 (PID: $BOB_PID)${NC}"
    
    echo ""
    echo "查看日志："
    echo "  tail -f simulation_test/logs/alice.log"
    echo "  tail -f simulation_test/logs/bob.log"
    echo ""
    echo "停止智能体："
    echo "  kill $ALICE_PID $BOB_PID"
fi

echo ""
echo "=========================================="
