#!/bin/bash

# API 服务器快速重启脚本

echo "================================================"
echo "重启 API 服务器"
echo "================================================"

# 停止 API 服务器
echo ""
echo "1. 停止 API 服务器..."
pkill -f "uvicorn main:app"

if [ $? -eq 0 ]; then
    echo "   ✅ 旧服务器已停止"
else
    echo "   ⚠️  没有找到运行中的服务器"
fi

# 等待进程完全结束
echo ""
echo "2. 等待进程结束..."
sleep 2

# 启动 API 服务器
echo ""
echo "3. 启动 API 服务器..."
nohup uvicorn main:app --host 0.0.0.0 --port 8080 > logs/api.log 2>&1 &

if [ $? -eq 0 ]; then
    echo "   ✅ 服务器已启动"
else
    echo "   ❌ 服务器启动失败"
    exit 1
fi

# 等待启动
sleep 3

# 检查状态
echo ""
echo "4. 检查服务器状态..."
if ps aux | grep -v grep | grep "uvicorn main:app" > /dev/null; then
    echo "   ✅ 服务器正在运行"
    
    # 显示进程信息
    echo ""
    echo "进程信息:"
    ps aux | grep -v grep | grep "uvicorn main:app" | awk '{print "   PID: " $2 ", CPU: " $3 "%, MEM: " $4 "%"}'
    
    # 测试 API
    echo ""
    echo "5. 测试 API 端点..."
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "   ✅ API 响应正常"
    else
        echo "   ⚠️  API 可能还在启动中"
    fi
else
    echo "   ❌ 服务器未运行"
    echo ""
    echo "查看错误日志:"
    echo "  tail -20 logs/api.log"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ API 服务器重启完成"
echo "================================================"
echo ""
echo "访问地址:"
echo "  http://localhost:8080"
echo ""
echo "查看日志:"
echo "  tail -f logs/api.log"
echo ""
echo "管理后台:"
echo "  http://localhost:8080/admin.html"
echo ""
