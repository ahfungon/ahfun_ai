#!/bin/bash

# Celery Worker 快速重启脚本（用于 API 调用）

# 停止 Worker（静默模式）
pkill -f "celery -A workers.celery_app worker" 2>/dev/null

# 短暂等待
sleep 1

# 后台启动 Worker（不等待）
nohup celery -A workers.celery_app worker --loglevel=info --logfile=logs/worker.log > /dev/null 2>&1 &

# 立即返回
echo "Worker restart initiated"
exit 0
