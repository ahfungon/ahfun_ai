#!/bin/bash

# 测试监控页面更新功能
# 验证新增的 API 端点和前端功能

echo "=========================================="
echo "监控页面更新功能测试"
echo "=========================================="
echo ""

API_URL="http://localhost:8000/api"

# 测试 1: 获取已关闭话题列表
echo "1. 测试获取已关闭话题列表"
echo "------------------------------------------"
echo "请求: GET ${API_URL}/monitor/topics/closed?limit=5"
echo ""

response=$(curl -s "${API_URL}/monitor/topics/closed?limit=5")
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

echo ""
echo ""

# 测试 2: 获取当前活跃话题
echo "2. 测试获取当前活跃话题"
echo "------------------------------------------"
echo "请求: GET ${API_URL}/monitor/topic/active"
echo ""

response=$(curl -s "${API_URL}/monitor/topic/active")
topic_id=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('topic_id', ''))" 2>/dev/null)

if [ -n "$topic_id" ]; then
    echo "✓ 找到活跃话题: $topic_id"
    echo ""
    echo "话题信息:"
    echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  标题: {data.get('title', 'N/A')}\")
print(f\"  状态: {data.get('status', 'N/A')}\")
print(f\"  描述: {data.get('topic_description', 'N/A')[:80]}...\")
print(f\"  评分: {data.get('end_score', 0)}\")
" 2>/dev/null || echo "$response"
else
    echo "✗ 没有活跃话题"
fi

echo ""
echo ""

# 测试 3: 获取特定话题详情（如果有活跃话题）
if [ -n "$topic_id" ]; then
    echo "3. 测试获取话题详情"
    echo "------------------------------------------"
    echo "请求: GET ${API_URL}/monitor/topic/${topic_id}"
    echo ""
    
    response=$(curl -s "${API_URL}/monitor/topic/${topic_id}")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    
    echo ""
    echo ""
fi

# 测试 4: 前端页面访问测试
echo "4. 前端页面访问测试"
echo "------------------------------------------"
echo "监控页面 URL: http://localhost:8000/frontend/monitor.html"
echo ""
echo "请在浏览器中打开上述 URL 进行测试："
echo ""
echo "✓ 检查话题简介是否显示在顶部"
echo "✓ 点击导航栏的'历史'按钮"
echo "✓ 查看历史话题列表是否正常显示"
echo "✓ 点击任意历史话题查看详情"
echo "✓ 验证模态框关闭功能"
echo ""

# 测试 5: API 响应时间测试
echo "5. API 响应时间测试"
echo "------------------------------------------"

echo -n "获取已关闭话题列表: "
time_start=$(date +%s%N)
curl -s "${API_URL}/monitor/topics/closed?limit=20" > /dev/null
time_end=$(date +%s%N)
time_diff=$(( (time_end - time_start) / 1000000 ))
echo "${time_diff}ms"

echo -n "获取活跃话题: "
time_start=$(date +%s%N)
curl -s "${API_URL}/monitor/topic/active" > /dev/null
time_end=$(date +%s%N)
time_diff=$(( (time_end - time_start) / 1000000 ))
echo "${time_diff}ms"

echo ""
echo ""

# 总结
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "新功能说明："
echo "1. 话题简介优先显示在话题信息卡片顶部"
echo "2. 导航栏新增'历史'按钮，可查看已关闭话题"
echo "3. 点击历史话题可查看完整讨论内容"
echo "4. 新增 API 端点："
echo "   - GET /api/monitor/topics/closed"
echo "   - GET /api/monitor/topic/{topic_id}"
echo ""
echo "详细说明请查看: 监控页面更新说明.md"
echo ""
