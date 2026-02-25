# API 服务器重启说明

## 问题

添加新的 API 端点后，前端访问时返回 404 错误：
```
GET http://localhost:8080/api/admin/summary/stats 404 (Not Found)
```

## 原因

API 服务器（uvicorn）没有自动重载功能（`--reload` 标志未启用），因此修改代码后需要手动重启才能加载新的端点。

## 解决方案

### 1. 查找运行中的 API 服务器进程

```bash
# 查找监听 8080 端口的进程
lsof -i :8080 2>/dev/null | grep LISTEN

# 或者查找 uvicorn 进程
ps aux | grep "uvicorn main:app" | grep -v grep
```

### 2. 停止旧的服务器

```bash
# 使用 PID 停止进程
kill <PID>

# 例如：
kill 87417
```

### 3. 启动新的服务器

```bash
# 在后台启动 API 服务器
nohup uvicorn main:app --host 0.0.0.0 --port 8080 > logs/api.log 2>&1 &

# 或者使用 main.py（默认端口 8000）
python3 main.py &
```

### 4. 验证服务器已启动

```bash
# 检查进程
ps aux | grep "uvicorn" | grep -v grep

# 测试 API 端点
curl http://localhost:8080/api/admin/summary/stats
```

## 快速重启脚本

创建一个快速重启脚本 `restart_api.sh`：

```bash
#!/bin/bash

echo "停止 API 服务器..."
pkill -f "uvicorn main:app"

sleep 2

echo "启动 API 服务器..."
nohup uvicorn main:app --host 0.0.0.0 --port 8080 > logs/api.log 2>&1 &

sleep 3

echo "检查服务器状态..."
if ps aux | grep -v grep | grep "uvicorn main:app" > /dev/null; then
    echo "✅ API 服务器已启动"
    echo "   访问: http://localhost:8080"
    echo "   日志: tail -f logs/api.log"
else
    echo "❌ API 服务器启动失败"
    echo "   查看日志: cat logs/api.log"
fi
```

使用方法：
```bash
chmod +x restart_api.sh
./restart_api.sh
```

## 开发模式（自动重载）

如果需要在开发时自动重载，可以添加 `--reload` 标志：

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

**注意**: `--reload` 模式会在检测到代码变化时自动重启服务器，但会消耗更多资源，不建议在生产环境使用。

## 生产环境部署

在生产环境中，建议使用进程管理工具：

### 使用 systemd

创建 `/etc/systemd/system/ahfun-api.service`：

```ini
[Unit]
Description=AhFun AI API Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/ahfun_ai
Environment="PATH=/path/to/ahfun_ai/venv/bin"
ExecStart=/path/to/ahfun_ai/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

管理命令：
```bash
sudo systemctl start ahfun-api
sudo systemctl stop ahfun-api
sudo systemctl restart ahfun-api
sudo systemctl status ahfun-api
```

### 使用 supervisor

创建 `/etc/supervisor/conf.d/ahfun-api.conf`：

```ini
[program:ahfun-api]
command=/path/to/ahfun_ai/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
directory=/path/to/ahfun_ai
user=your-user
autostart=true
autorestart=true
stderr_logfile=/var/log/ahfun-api.err.log
stdout_logfile=/var/log/ahfun-api.out.log
```

管理命令：
```bash
sudo supervisorctl start ahfun-api
sudo supervisorctl stop ahfun-api
sudo supervisorctl restart ahfun-api
sudo supervisorctl status ahfun-api
```

## 常见问题

### 1. 端口已被占用

错误信息：`[Errno 48] Address already in use`

解决方法：
```bash
# 查找占用端口的进程
lsof -i :8080 | grep LISTEN

# 停止该进程
kill <PID>
```

### 2. 权限不足

错误信息：`Permission denied`

解决方法：
```bash
# 确保日志目录存在且有写权限
mkdir -p logs
chmod 755 logs
```

### 3. 模块导入错误

错误信息：`ModuleNotFoundError`

解决方法：
```bash
# 确保在正确的虚拟环境中
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 总结

- 修改 API 代码后，必须重启 API 服务器才能生效
- 使用 `--reload` 标志可以在开发时自动重载
- 生产环境建议使用 systemd 或 supervisor 管理进程
- 定期检查日志文件 `logs/api.log` 以排查问题
