#!/bin/bash

# 测试智能体优化效果

echo "=========================================="
echo "智能体优化效果测试"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}1. 检查代码语法...${NC}"
python3 -m py_compile simulation_test/autonomous_agent.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 语法检查通过${NC}"
else
    echo -e "${RED}✗ 语法错误${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}2. 检查新增方法...${NC}"
if grep -q "get_topic_summary_history" simulation_test/autonomous_agent.py; then
    echo -e "${GREEN}✓ 找到 get_topic_summary_history() 方法${NC}"
else
    echo -e "${RED}✗ 未找到 get_topic_summary_history() 方法${NC}"
fi

echo ""
echo -e "${YELLOW}3. 检查关键优化点...${NC}"

# 检查是否添加了话题总结
if grep -q "【话题总结】" simulation_test/autonomous_agent.py; then
    echo -e "${GREEN}✓ 已添加话题总结到 LLM prompt${NC}"
else
    echo -e "${YELLOW}○ 未找到话题总结${NC}"
fi

# 检查是否添加了系统建议
if grep -q "【系统建议】" simulation_test/autonomous_agent.py; then
    echo -e "${GREEN}✓ 已添加系统建议到 LLM prompt${NC}"
else
    echo -e "${YELLOW}○ 未找到系统建议${NC}"
fi

# 检查是否添加了讨论演进
if grep -q "【讨论演进】" simulation_test/autonomous_agent.py; then
    echo -e "${GREEN}✓ 已添加讨论演进分析${NC}"
else
    echo -e "${YELLOW}○ 未找到讨论演进${NC}"
fi

# 检查是否添加了评分建议
if grep -q "评分优秀" simulation_test/autonomous_agent.py; then
    echo -e "${GREEN}✓ 已添加评分驱动的改进建议${NC}"
else
    echo -e "${YELLOW}○ 未找到评分建议${NC}"
fi

# 检查是否添加了避免重复的要求
if grep -q "避免重复" simulation_test/autonomous_agent.py; then
    echo -e "${GREEN}✓ 已添加避免重复的要求${NC}"
else
    echo -e "${YELLOW}○ 未找到避免重复要求${NC}"
fi

echo ""
echo -e "${YELLOW}4. 对比代码行数...${NC}"
if [ -f "simulation_test/autonomous_agent.py.backup" ]; then
    OLD_LINES=$(wc -l < simulation_test/autonomous_agent.py.backup)
    NEW_LINES=$(wc -l < simulation_test/autonomous_agent.py)
    DIFF=$((NEW_LINES - OLD_LINES))
    
    echo -e "  优化前: ${OLD_LINES} 行"
    echo -e "  优化后: ${NEW_LINES} 行"
    echo -e "  增加: ${GREEN}+${DIFF}${NC} 行"
else
    echo -e "${YELLOW}  备份文件不存在，跳过对比${NC}"
fi

echo ""
echo -e "${YELLOW}5. 检查智能体运行状态...${NC}"
ALICE_PID=$(pgrep -f "autonomous_agent.py --agent alice" | head -1)
BOB_PID=$(pgrep -f "autonomous_agent.py --agent bob" | head -1)

if [ -n "$ALICE_PID" ]; then
    echo -e "${GREEN}✓ Agent-Alice 运行中 (PID: $ALICE_PID)${NC}"
    echo -e "${YELLOW}  建议: 重启以应用优化${NC}"
else
    echo -e "${BLUE}○ Agent-Alice 未运行${NC}"
fi

if [ -n "$BOB_PID" ]; then
    echo -e "${GREEN}✓ Agent-Bob 运行中 (PID: $BOB_PID)${NC}"
    echo -e "${YELLOW}  建议: 重启以应用优化${NC}"
else
    echo -e "${BLUE}○ Agent-Bob 未运行${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}测试完成！${NC}"
echo "=========================================="

echo ""
echo "下一步操作："
echo ""
echo "1. 重启智能体以应用优化:"
echo "   pkill -f 'autonomous_agent.py'"
echo "   cd simulation_test && ./start_agents.sh"
echo ""
echo "2. 观察日志输出:"
echo "   tail -f simulation_test/logs/agent-alice.log"
echo ""
echo "3. 查看前端监控:"
echo "   http://localhost:8080"
echo ""
echo "4. 查看详细报告:"
echo "   cat 智能体优化完成报告.md"
echo ""
