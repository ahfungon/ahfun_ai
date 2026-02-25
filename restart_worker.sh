#!/bin/bash

# Celery Worker 重启脚本

echo "================================================"
echo "重启 Celery Worker"
echo "================================================"

# 停止 Worker
echo ""
echo "1. 停止 Celery Worker..."
pkill -f "celery -A workers.celery_app worker"

if [ $? -eq 0 ]; then
    echo "   ✅ Worker 进程已停止"
else
    echo "   ⚠️  没有找到运行中的 Worker 进程"
fi

# 等待进程完全结束
echo ""
echo "2. 等待进程结束..."
sleep 2

# 启动 Worker
echo ""
echo "3. 启动 Celery Worker..."
# 指定监听所有队列：default, summary_jobs, periodic_tasks
celery -A workers.celery_app worker --loglevel=info --logfile=logs/worker.log -Q default,summary_jobs,periodic_tasks &

if [ $? -eq 0 ]; then
    echo "   ✅ Worker 已启动"
else
    echo "   ❌ Worker 启动失败"
    exit 1
fi

# 等待启动
sleep 2

# 检查状态
echo ""
echo "4. 检查 Worker 状态..."
if ps aux | grep -v grep | grep "celery.*worker" > /dev/null; then
    echo "   ✅ Worker 正在运行"
    
    # 显示进程信息
    echo ""
    echo "进程信息:"
    ps aux | grep -v grep | grep "celery.*worker" | awk '{print "   PID: " $2 ", CPU: " $3 "%, MEM: " $4 "%"}'
else
    echo "   ❌ Worker 未运行"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ Worker 重启完成"
echo "================================================"
echo ""
echo "查看日志:"
echo "  tail -f logs/worker.log"
echo ""
echo "查看 LLM 调用:"
echo "  tail -f logs/worker.log | grep -i 'minimax\\|deepseek'"
echo ""
