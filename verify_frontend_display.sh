#!/bin/bash

# 前端显示功能验证脚本
# 用于验证服务器上的前端是否正确显示话题信息

echo "=========================================="
echo "前端显示功能验证脚本"
echo "=========================================="
echo ""

# 服务器地址
SERVER_URL="http://129.211.28.211:8080"

echo "1. 检查 API 响应..."
echo "---"
API_RESPONSE=$(curl -s "${SERVER_URL}/api/monitor/topic/active")

if [ $? -ne 0 ]; then
    echo "❌ 无法连接到服务器"
    exit 1
fi

echo "✅ API 连接成功"
echo ""

# 检查必要字段
echo "2. 检查 API 返回的关键字段..."
echo "---"

# 检查 llm_suggestion
if echo "$API_RESPONSE" | grep -q '"llm_suggestion"'; then
    LLM_SUGGESTION=$(echo "$API_RESPONSE" | grep -o '"llm_suggestion":"[^"]*"' | cut -d'"' -f4)
    echo "✅ llm_suggestion: $LLM_SUGGESTION"
else
    echo "❌ 缺少 llm_suggestion 字段"
fi

# 检查 end_score
if echo "$API_RESPONSE" | grep -q '"end_score"'; then
    END_SCORE=$(echo "$API_RESPONSE" | grep -o '"end_score":[0-9.]*' | cut -d':' -f2)
    echo "✅ end_score: $END_SCORE"
else
    echo "❌ 缺少 end_score 字段"
fi

# 检查 summary
if echo "$API_RESPONSE" | grep -q '"summary"'; then
    SUMMARY_LENGTH=$(echo "$API_RESPONSE" | grep -o '"summary":"[^"]*"' | wc -c)
    echo "✅ summary: 存在 (长度: $SUMMARY_LENGTH 字符)"
else
    echo "❌ 缺少 summary 字段"
fi

# 检查 llm_hint
if echo "$API_RESPONSE" | grep -q '"llm_hint"'; then
    LLM_HINT=$(echo "$API_RESPONSE" | grep -o '"llm_hint":"[^"]*"' | cut -d'"' -f4)
    echo "✅ llm_hint: $LLM_HINT"
else
    echo "⚠️  llm_hint 字段为空（可能正常，取决于状态）"
fi

echo ""
echo "3. 完整 API 响应（格式化）..."
echo "---"
echo "$API_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$API_RESPONSE"

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "如果所有字段都显示 ✅，但前端仍然看不到信息，请："
echo "1. 在服务器上执行: git pull origin main"
echo "2. 重启服务"
echo "3. 在浏览器中按 Ctrl+Shift+R 强制刷新"
echo ""
echo "如果有字段显示 ❌，请检查后端服务是否正常运行"
