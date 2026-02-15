#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器配置
SERVER_IP="129.211.28.211"
SERVER_USER="ubuntu"
SSH_KEY="~/.ssh/mingkuan.pem"

echo "=========================================="
echo "部署前环境检查"
echo "=========================================="

ERRORS=0
WARNINGS=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# 1. 本地环境检查
echo ""
echo "=== 本地环境检查 ==="

# 检查 SSH 密钥
echo -n "检查 SSH 密钥... "
if [ -f ~/.ssh/mingkuan.pem ]; then
    check_pass "SSH 密钥存在"
    
    # 检查密钥权限
    PERMS=$(stat -f "%A" ~/.ssh/mingkuan.pem 2>/dev/null || stat -c "%a" ~/.ssh/mingkuan.pem 2>/dev/null)
    if [ "$PERMS" = "600" ] || [ "$PERMS" = "400" ]; then
        check_pass "SSH 密钥权限正确 ($PERMS)"
    else
        check_warn "SSH 密钥权限不正确 ($PERMS)，建议设置为 600"
        echo "  运行: chmod 600 ~/.ssh/mingkuan.pem"
    fi
else
    check_fail "SSH 密钥不存在: ~/.ssh/mingkuan.pem"
fi

# 检查 .env 文件
echo -n "检查 .env 文件... "
if [ -f ".env" ]; then
    check_pass ".env 文件存在"
    
    # 检查必要的环境变量
    REQUIRED_VARS=("DATABASE_URL" "REDIS_URL" "DEEPSEEK_API_KEY")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env; then
            check_pass "  ${var} 已配置"
        else
            check_warn "  ${var} 未配置"
        fi
    done
else
    check_fail ".env 文件不存在"
fi

# 检查 pg_dump
echo -n "检查 pg_dump... "
if command -v pg_dump &> /dev/null; then
    check_pass "pg_dump 已安装"
else
    check_warn "pg_dump 未安装，将跳过数据库导出"
fi

# 检查 rsync
echo -n "检查 rsync... "
if command -v rsync &> /dev/null; then
    check_pass "rsync 已安装"
else
    check_fail "rsync 未安装，请先安装: brew install rsync"
fi

# 2. 服务器连接检查
echo ""
echo "=== 服务器连接检查 ==="

echo -n "测试 SSH 连接... "
if ssh -i ~/.ssh/mingkuan.pem -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} 'echo "连接成功"' &> /dev/null; then
    check_pass "SSH 连接成功"
else
    check_fail "SSH 连接失败"
    echo "  请检查："
    echo "  1. 密钥路径是否正确"
    echo "  2. 服务器 IP 是否正确"
    echo "  3. 网络连接是否正常"
fi

# 3. 服务器环境检查
if [ $ERRORS -eq 0 ]; then
    echo ""
    echo "=== 服务器环境检查 ==="
    
    # 检查磁盘空间
    echo -n "检查磁盘空间... "
    DISK_USAGE=$(ssh -i ~/.ssh/mingkuan.pem ${SERVER_USER}@${SERVER_IP} "df -h / | tail -1 | awk '{print \$5}' | sed 's/%//'" 2>/dev/null)
    if [ -n "$DISK_USAGE" ]; then
        if [ "$DISK_USAGE" -lt 80 ]; then
            check_pass "磁盘使用率: ${DISK_USAGE}%"
        else
            check_warn "磁盘使用率较高: ${DISK_USAGE}%"
        fi
    else
        check_warn "无法检查磁盘空间"
    fi
    
    # 检查服务状态
    echo "检查服务状态..."
    ssh -i ~/.ssh/mingkuan.pem ${SERVER_USER}@${SERVER_IP} << 'ENDSSH' 2>/dev/null
    
    # PostgreSQL
    if systemctl is-active --quiet postgresql; then
        echo "✓ PostgreSQL 运行中"
    else
        echo "✗ PostgreSQL 未运行"
    fi
    
    # Redis
    if systemctl is-active --quiet redis-server; then
        echo "✓ Redis 运行中"
    else
        echo "✗ Redis 未运行"
    fi
    
    # Nginx
    if systemctl is-active --quiet nginx; then
        echo "✓ Nginx 运行中"
    else
        echo "✗ Nginx 未运行"
    fi
    
    # Python
    if command -v python3 &> /dev/null; then
        echo "✓ Python $(python3 --version | cut -d' ' -f2) 已安装"
    else
        echo "✗ Python 未安装"
    fi
    
ENDSSH
    
    # 检查应用目录
    echo -n "检查应用目录... "
    if ssh -i ~/.ssh/mingkuan.pem ${SERVER_USER}@${SERVER_IP} "[ -d ~/dual-agent-chat ]" 2>/dev/null; then
        check_pass "应用目录存在"
    else
        check_warn "应用目录不存在，将在部署时创建"
    fi
    
    # 检查端口 8080
    echo -n "检查端口 8080... "
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://${SERVER_IP}:8080 | grep -q "200\|404\|502"; then
        check_pass "端口 8080 可访问"
    else
        check_warn "端口 8080 无法访问，请检查防火墙设置"
    fi
fi

# 4. 本地数据库检查
echo ""
echo "=== 本地数据库检查 ==="

if command -v psql &> /dev/null; then
    echo -n "测试数据库连接... "
    if PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -c "SELECT 1;" &> /dev/null; then
        check_pass "数据库连接成功"
        
        # 统计数据
        echo "数据统计:"
        PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -t -c "
        SELECT 
            '  话题数: ' || COUNT(*) FROM topics
        UNION ALL
        SELECT 
            '  消息数: ' || COUNT(*) FROM messages
        UNION ALL
        SELECT 
            '  智能体数: ' || COUNT(*) FROM agents;
        " 2>/dev/null
    else
        check_warn "数据库连接失败，将使用空数据库"
    fi
else
    check_warn "psql 未安装，跳过数据库检查"
fi

# 总结
echo ""
echo "=========================================="
echo "检查完成"
echo "=========================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过，可以开始部署！${NC}"
    echo ""
    echo "执行部署命令："
    echo "  ./deploy_to_mingkuan.sh"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ 发现 ${WARNINGS} 个警告，建议检查后再部署${NC}"
    echo ""
    echo "如果确认无误，执行部署命令："
    echo "  ./deploy_to_mingkuan.sh"
    exit 0
else
    echo -e "${RED}✗ 发现 ${ERRORS} 个错误，${WARNINGS} 个警告${NC}"
    echo ""
    echo "请修复错误后再尝试部署"
    exit 1
fi
