#!/bin/bash

# 管理后台话题管理功能测试脚本

echo "=========================================="
echo "管理后台话题管理功能测试"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8080/api"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_case() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${YELLOW}测试 $TOTAL_TESTS: $1${NC}"
}

test_pass() {
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✓ 通过${NC}"
    echo ""
}

test_fail() {
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}✗ 失败: $1${NC}"
    echo ""
}

# 测试 1: 创建话题（完整信息）
test_case "创建话题（带标题和描述）"
RESPONSE=$(curl -s -X POST "$BASE_URL/admin/topic" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "测试话题1：AI技术讨论",
    "topic_description": "这是一个测试话题，用于讨论AI技术的应用和发展。"
  }')

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    TOPIC_ID_1=$(echo "$RESPONSE" | grep -o '"topic_id":"[^"]*"' | cut -d'"' -f4)
    echo "话题ID: $TOPIC_ID_1"
    test_pass
else
    test_fail "创建失败"
    echo "$RESPONSE"
fi

# 测试 2: 创建话题（仅标题）
test_case "创建话题（仅标题）"
RESPONSE=$(curl -s -X POST "$BASE_URL/admin/topic" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "测试话题2：简单话题"
  }')

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    TOPIC_ID_2=$(echo "$RESPONSE" | grep -o '"topic_id":"[^"]*"' | cut -d'"' -f4)
    echo "话题ID: $TOPIC_ID_2"
    test_pass
else
    test_fail "创建失败"
    echo "$RESPONSE"
fi

# 测试 3: 创建话题（空标题，应该失败）
test_case "创建话题（空标题，预期失败）"
RESPONSE=$(curl -s -X POST "$BASE_URL/admin/topic" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": ""
  }')

if echo "$RESPONSE" | grep -q '"detail":"Title is required"'; then
    test_pass
else
    test_fail "应该返回错误"
    echo "$RESPONSE"
fi

# 测试 4: 查询话题列表
test_case "查询话题列表"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/topics?limit=10")

if echo "$RESPONSE" | grep -q '"total":2'; then
    echo "找到 2 个话题"
    test_pass
else
    test_fail "话题数量不正确"
    echo "$RESPONSE"
fi

# 测试 5: 查询话题详情
test_case "查询话题详情"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/topic/$TOPIC_ID_1")

if echo "$RESPONSE" | grep -q '"topic_id":"'$TOPIC_ID_1'"'; then
    echo "话题详情获取成功"
    test_pass
else
    test_fail "获取详情失败"
    echo "$RESPONSE"
fi

# 测试 6: 修改话题
test_case "修改话题标题和描述"
RESPONSE=$(curl -s -X PUT "$BASE_URL/admin/topic/$TOPIC_ID_1" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "测试话题1：AI技术深度讨论（已修改）",
    "topic_description": "这是一个修改后的测试话题描述。"
  }')

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo "话题修改成功"
    test_pass
else
    test_fail "修改失败"
    echo "$RESPONSE"
fi

# 测试 7: 验证修改结果
test_case "验证修改结果"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/topic/$TOPIC_ID_1")

if echo "$RESPONSE" | grep -q "已修改"; then
    echo "修改已生效"
    test_pass
else
    test_fail "修改未生效"
    echo "$RESPONSE"
fi

# 测试 8: 按状态筛选话题
test_case "按状态筛选话题（active）"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/topics?status=active&limit=10")

if echo "$RESPONSE" | grep -q '"status":"active"'; then
    echo "筛选成功"
    test_pass
else
    test_fail "筛选失败"
    echo "$RESPONSE"
fi

# 测试 9: 删除话题
test_case "删除话题"
RESPONSE=$(curl -s -X DELETE "$BASE_URL/admin/topic/$TOPIC_ID_1")

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo "话题删除成功"
    test_pass
else
    test_fail "删除失败"
    echo "$RESPONSE"
fi

# 测试 10: 验证删除结果
test_case "验证话题已删除"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/topic/$TOPIC_ID_1")

if echo "$RESPONSE" | grep -q '"detail":"Topic.*not found"'; then
    echo "话题已被删除"
    test_pass
else
    test_fail "话题仍然存在"
    echo "$RESPONSE"
fi

# 测试 11: 删除第二个话题
test_case "删除第二个话题"
RESPONSE=$(curl -s -X DELETE "$BASE_URL/admin/topic/$TOPIC_ID_2")

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo "话题删除成功"
    test_pass
else
    test_fail "删除失败"
    echo "$RESPONSE"
fi

# 测试 12: 验证所有话题已删除
test_case "验证所有测试话题已删除"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/topics?limit=10")

if echo "$RESPONSE" | grep -q '"total":0'; then
    echo "所有测试话题已清理"
    test_pass
else
    test_fail "仍有话题存在"
    echo "$RESPONSE"
fi

# 测试 13: 删除不存在的话题（应该失败）
test_case "删除不存在的话题（预期失败）"
RESPONSE=$(curl -s -X DELETE "$BASE_URL/admin/topic/non-existent-id")

if echo "$RESPONSE" | grep -q '"detail":"Topic.*not found"'; then
    test_pass
else
    test_fail "应该返回404错误"
    echo "$RESPONSE"
fi

# 输出测试结果
echo "=========================================="
echo "测试结果汇总"
echo "=========================================="
echo -e "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 有测试失败${NC}"
    exit 1
fi
