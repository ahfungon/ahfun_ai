#!/bin/bash

# 加载环境变量
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# 确保 DEEPSEEK_API_KEY 已设置
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ DEEPSEEK_API_KEY 未设置"
    echo "请运行: source .env && export DEEPSEEK_API_KEY"
    exit 1
fi

echo "✅ DEEPSEEK_API_KEY 已设置 (${#DEEPSEEK_API_KEY} 字符)"
echo "启动 Agent-Alice..."

# 启动智能体
python3 autonomous_agent.py --agent alice
