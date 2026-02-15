#!/bin/bash
# 启动自主智能体的便捷脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 自主智能体启动脚本${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  DEEPSEEK_API_KEY 未设置${NC}"
    echo -e "${YELLOW}   正在从 .env 文件加载...${NC}"
    
    if [ -f "../.env" ]; then
        source ../.env
        export DEEPSEEK_API_KEY
        echo -e "${GREEN}✓ API 密钥已加载${NC}"
    else
        echo -e "${RED}❌ .env 文件不存在${NC}"
        echo -e "${RED}   请设置 DEEPSEEK_API_KEY 环境变量${NC}"
        exit 1
    fi
fi

# 检查服务状态
echo ""
echo -e "${BLUE}📡 检查服务状态...${NC}"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 服务正常运行${NC}"
else
    echo -e "${RED}❌ 服务未运行${NC}"
    echo -e "${YELLOW}   请先启动服务: ./start_services.sh${NC}"
    exit 1
fi

# 检查活跃话题
echo ""
echo -e "${BLUE}🔍 检查活跃话题...${NC}"
if curl -s "http://localhost:8000/api/topic/active" \
    -H "X-Agent-Id: test" \
    -H "X-Auth-Token: test" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 找到活跃话题${NC}"
else
    echo -e "${YELLOW}⚠️  没有活跃话题${NC}"
    echo -e "${YELLOW}   建议先创建话题: python simulation_test/enhanced_simulator.py --rounds 3${NC}"
fi

# 显示可用智能体
echo ""
echo -e "${BLUE}🤖 可用智能体:${NC}"
echo -e "  ${GREEN}alice${NC}  - 分析型 (注重数据和证据)"
echo -e "  ${GREEN}bob${NC}    - 创造型 (富有创造力和前瞻性)"
echo -e "  ${GREEN}carol${NC}  - 实用型 (注重实践和应用)"

# 选择启动方式
echo ""
echo -e "${BLUE}请选择启动方式:${NC}"
echo "  1) 启动单个智能体（前台运行）"
echo "  2) 启动两个智能体（后台运行）"
echo "  3) 启动所有智能体（后台运行）"
echo "  4) 查看运行中的智能体"
echo "  5) 停止所有智能体"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo ""
        read -p "请输入智能体名称 (alice/bob/carol): " agent
        echo ""
        echo -e "${GREEN}🚀 启动 $agent...${NC}"
        echo -e "${YELLOW}   按 Ctrl+C 停止${NC}"
        echo ""
        python autonomous_agent.py --agent $agent
        ;;
    
    2)
        echo ""
        echo -e "${GREEN}🚀 启动 Alice 和 Bob (后台运行)...${NC}"
        nohup python autonomous_agent.py --agent alice > /dev/null 2>&1 &
        ALICE_PID=$!
        nohup python autonomous_agent.py --agent bob > /dev/null 2>&1 &
        BOB_PID=$!
        
        echo -e "${GREEN}✓ Alice 已启动 (PID: $ALICE_PID)${NC}"
        echo -e "${GREEN}✓ Bob 已启动 (PID: $BOB_PID)${NC}"
        echo ""
        echo -e "${BLUE}查看日志:${NC}"
        echo "  tail -f logs/agent-alice.log"
        echo "  tail -f logs/agent-bob.log"
        echo ""
        echo -e "${BLUE}停止智能体:${NC}"
        echo "  kill $ALICE_PID $BOB_PID"
        ;;
    
    3)
        echo ""
        echo -e "${GREEN}🚀 启动所有智能体 (后台运行)...${NC}"
        nohup python autonomous_agent.py --agent alice > /dev/null 2>&1 &
        echo -e "${GREEN}✓ Alice 已启动 (PID: $!)${NC}"
        nohup python autonomous_agent.py --agent bob > /dev/null 2>&1 &
        echo -e "${GREEN}✓ Bob 已启动 (PID: $!)${NC}"
        nohup python autonomous_agent.py --agent carol > /dev/null 2>&1 &
        echo -e "${GREEN}✓ Carol 已启动 (PID: $!)${NC}"
        echo ""
        echo -e "${BLUE}查看日志:${NC}"
        echo "  tail -f logs/agent-*.log"
        ;;
    
    4)
        echo ""
        echo -e "${BLUE}运行中的智能体:${NC}"
        ps aux | grep "autonomous_agent.py" | grep -v grep | while read line; do
            echo "  $line"
        done
        ;;
    
    5)
        echo ""
        echo -e "${YELLOW}🛑 停止所有智能体...${NC}"
        pkill -f "autonomous_agent.py"
        echo -e "${GREEN}✓ 已停止${NC}"
        ;;
    
    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
