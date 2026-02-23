#!/bin/bash

# 实时监控双智能体对话

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 实时监控双智能体对话"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 智能体状态:"
echo "  🔍 Alice (分析型) - 注重数据和证据"
echo "  💡 Bob (创造型) - 提出创新想法"
echo ""
echo "💡 提示:"
echo "  - 按 Ctrl+C 停止监控"
echo "  - 日志会实时滚动显示"
echo "  - 🔍 = Alice 发言"
echo "  - 💡 = Bob 发言"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 实时监控两个智能体的日志
tail -f simulation_test/logs/agent-alice.log simulation_test/logs/agent-bob.log | \
while read line; do
    # 根据内容添加颜色
    if [[ $line == *"Agent-Alice"* ]]; then
        echo -e "\033[36m$line\033[0m"  # 青色
    elif [[ $line == *"Agent-Bob"* ]]; then
        echo -e "\033[35m$line\033[0m"  # 紫色
    elif [[ $line == *"✓"* ]]; then
        echo -e "\033[32m$line\033[0m"  # 绿色
    elif [[ $line == *"❌"* ]] || [[ $line == *"错误"* ]]; then
        echo -e "\033[31m$line\033[0m"  # 红色
    elif [[ $line == *"🤔"* ]] || [[ $line == *"LLM"* ]]; then
        echo -e "\033[33m$line\033[0m"  # 黄色
    else
        echo "$line"
    fi
done
