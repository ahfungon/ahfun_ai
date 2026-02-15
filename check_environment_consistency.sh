#!/bin/bash
set -e

echo "=========================================="
echo "环境一致性检查"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ERRORS=0

# 1. 检查文件一致性
echo ""
echo -e "${YELLOW}[1/5] 检查文件一致性...${NC}"

if [ -f "frontend/ai-agent-guide.html" ] && [ -f "static/ai-agent-guide.html" ]; then
    if diff -q frontend/ai-agent-guide.html static/ai-agent-guide.html > /dev/null; then
        echo -e "${GREEN}✓ frontend/ai-agent-guide.html 和 static/ai-agent-guide.html 内容一致${NC}"
    else
        echo -e "${RED}✗ frontend/ai-agent-guide.html 和 static/ai-agent-guide.html 内容不一致${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}✗ ai-agent-guide.html 文件缺失${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 2. 检查本地服务状态
echo ""
echo -e "${YELLOW}[2/5] 检查本地服务状态...${NC}"

if ps aux | grep -v grep | grep "uvicorn main:app" > /dev/null; then
    echo -e "${GREEN}✓ FastAPI 服务运行中 (端口 8000)${NC}"
else
    echo -e "${RED}✗ FastAPI 服务未运行${NC}"
    ERRORS=$((ERRORS + 1))
fi

if ps aux | grep -v grep | grep "nginx.*nginx_local.conf" > /dev/null; then
    echo -e "${GREEN}✓ Nginx 服务运行中 (端口 8080)${NC}"
else
    echo -e "${RED}✗ Nginx 服务未运行${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 3. 检查本地访问
echo ""
echo -e "${YELLOW}[3/5] 检查本地访问...${NC}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ai-agent-guide.html)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ http://localhost:8080/ai-agent-guide.html 可访问${NC}"
else
    echo -e "${RED}✗ http://localhost:8080/ai-agent-guide.html 返回 $HTTP_CODE${NC}"
    ERRORS=$((ERRORS + 1))
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/ai-agent-guide.html)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ http://localhost:8080/static/ai-agent-guide.html 可访问${NC}"
else
    echo -e "${RED}✗ http://localhost:8080/static/ai-agent-guide.html 返回 $HTTP_CODE${NC}"
    ERRORS=$((ERRORS + 1))
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/monitor.html)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ http://localhost:8080/monitor.html 可访问${NC}"
else
    echo -e "${RED}✗ http://localhost:8080/monitor.html 返回 $HTTP_CODE${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 4. 检查生产环境访问
echo ""
echo -e "${YELLOW}[4/5] 检查生产环境访问...${NC}"

SERVER_IP="129.211.28.211"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8080/ai-agent-guide.html)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ http://${SERVER_IP}:8080/ai-agent-guide.html 可访问${NC}"
else
    echo -e "${RED}✗ http://${SERVER_IP}:8080/ai-agent-guide.html 返回 $HTTP_CODE${NC}"
    ERRORS=$((ERRORS + 1))
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8080/static/ai-agent-guide.html)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ http://${SERVER_IP}:8080/static/ai-agent-guide.html 可访问${NC}"
else
    echo -e "${RED}✗ http://${SERVER_IP}:8080/static/ai-agent-guide.html 返回 $HTTP_CODE${NC}"
    ERRORS=$((ERRORS + 1))
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8080/monitor.html)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ http://${SERVER_IP}:8080/monitor.html 可访问${NC}"
else
    echo -e "${RED}✗ http://${SERVER_IP}:8080/monitor.html 返回 $HTTP_CODE${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 5. 检查 Nginx 配置一致性
echo ""
echo -e "${YELLOW}[5/5] 检查 Nginx 配置...${NC}"

if [ -f "nginx_local.conf" ]; then
    echo -e "${GREEN}✓ 本地 Nginx 配置文件存在${NC}"
    
    # 检查配置中的关键路径
    if grep -q "root.*frontend" nginx_local.conf; then
        echo -e "${GREEN}✓ Nginx 配置指向 frontend 目录${NC}"
    else
        echo -e "${RED}✗ Nginx 配置未正确指向 frontend 目录${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q "alias.*static" nginx_local.conf; then
        echo -e "${GREEN}✓ Nginx 配置包含 static 目录映射${NC}"
    else
        echo -e "${RED}✗ Nginx 配置缺少 static 目录映射${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}✗ 本地 Nginx 配置文件不存在${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 总结
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！本地和生产环境一致。${NC}"
else
    echo -e "${RED}✗ 发现 $ERRORS 个问题，请修复后重试。${NC}"
fi
echo "=========================================="

exit $ERRORS
