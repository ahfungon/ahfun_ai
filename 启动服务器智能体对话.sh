#!/bin/bash

# 启动服务器智能体对话
# 用法: ./启动服务器智能体对话.sh

echo "=========================================="
echo "启动服务器智能体对话"
echo "=========================================="

cd simulation_test

echo ""
echo "启动 Alice 和 Bob 智能体连接到服务器..."
echo "服务器地址: http://129.211.28.211:8080/api"
echo ""

# 启动智能体（使用 --env server 参数）
./start_agents.sh --env server

echo ""
echo "智能体已启动！"
echo ""
echo "监控方式："
echo "1. 查看监控页面: http://129.211.28.211:8080/monitor.html"
echo "2. 查看本地日志: tail -f simulation_test/logs/*.log"
echo "3. 停止智能体: pkill -f autonomous_agent.py"
echo ""
