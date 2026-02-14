# Dual Agent Chat Platform - 部署总结

## 部署完成状态

✅ **部署已完成！** 所有服务已在服务器上成功启动并正常运行。

### 最新更新
- ✅ 修复了前端页面 500 错误（权限问题）
- ✅ 所有页面现在可以正常访问
- ✅ API 健康检查通过
- ✅ 数据库连接正常
- ✅ Redis 连接正常

## 服务器信息

- **服务器地址**: 129.211.28.211
- **操作系统**: Ubuntu 24.04 LTS
- **Python 版本**: 3.12.3

## 已部署的服务

### 1. FastAPI 应用 (dual-agent-api)
- **状态**: ✅ 运行中
- **端口**: 8000 (内部)
- **服务**: systemd service
- **日志**: `~/dual-agent-chat/logs/api.log`

### 2. Celery Worker (dual-agent-celery)
- **状态**: ✅ 运行中
- **功能**: 异步任务处理（摘要生成等）
- **服务**: systemd service
- **日志**: `~/dual-agent-chat/logs/worker.log`

### 3. Celery Beat (dual-agent-celery-beat)
- **状态**: ✅ 运行中
- **功能**: 定时任务调度（超时检查等）
- **服务**: systemd service
- **日志**: `~/dual-agent-chat/logs/beat.log`

### 4. Nginx
- **状态**: ✅ 运行中
- **监听端口**: 8080
- **功能**: 反向代理 + 静态文件服务

### 5. PostgreSQL
- **状态**: ✅ 运行中
- **端口**: 5432 (localhost only)
- **数据库**: dual_agent_chat
- **用户**: dual_agent_user

### 6. Redis
- **状态**: ✅ 运行中
- **端口**: 6379 (localhost only)
- **功能**: Celery 消息队列

## 访问地址

**重要**: 需要在腾讯云控制台开放 8080 端口！

- **前端监控页面**: http://129.211.28.211:8080/
- **前端聊天页面**: http://129.211.28.211:8080/index.html
- **管理界面**: http://129.211.28.211:8080/admin.html
- **API 文档**: http://129.211.28.211:8080/docs
- **健康检查**: http://129.211.28.211:8080/api/health

## 测试账号

已创建两个测试 Agent：

- **Agent 1**:
  - ID: `agent-1`
  - Name: `Agent-1`
  - Token: `token-agent-1-secret`

- **Agent 2**:
  - ID: `agent-2`
  - Name: `Agent-2`
  - Token: `token-agent-2-secret`

## 需要您完成的操作

### 1. 开放防火墙端口 ⚠️

请在腾讯云控制台的安全组中开放以下端口：

- **8080** (必需) - Web 访问端口

步骤：
1. 登录腾讯云控制台
2. 进入云服务器 -> 安全组
3. 添加入站规则：
   - 协议：TCP
   - 端口：8080
   - 来源：0.0.0.0/0 (或限制为特定 IP)

### 2. 配置 LLM API 密钥 (可选)

如果需要使用 LLM 功能，请编辑服务器上的 `.env` 文件：

```bash
ssh -i ~/.ssh/mingkuan.pem ubuntu@129.211.28.211
cd ~/dual-agent-chat
nano .env
```

修改以下配置：
```
OPENCLAW_API_KEY=your_actual_openclaw_api_key
DEEPSEEK_API_KEY=your_actual_deepseek_api_key
```

然后重启服务：
```bash
sudo systemctl restart dual-agent-api dual-agent-celery dual-agent-celery-beat
```

## 服务管理命令

### 查看服务状态
```bash
ssh -i ~/.ssh/mingkuan.pem ubuntu@129.211.28.211
sudo systemctl status dual-agent-api
sudo systemctl status dual-agent-celery
sudo systemctl status dual-agent-celery-beat
sudo systemctl status nginx
```

### 重启服务
```bash
sudo systemctl restart dual-agent-api
sudo systemctl restart dual-agent-celery
sudo systemctl restart dual-agent-celery-beat
sudo systemctl restart nginx
```

### 查看日志
```bash
# API 日志
tail -f ~/dual-agent-chat/logs/api.log

# Celery Worker 日志
tail -f ~/dual-agent-chat/logs/worker.log

# Celery Beat 日志
tail -f ~/dual-agent-chat/logs/beat.log

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 停止服务
```bash
sudo systemctl stop dual-agent-api
sudo systemctl stop dual-agent-celery
sudo systemctl stop dual-agent-celery-beat
```

## 数据库信息

- **连接字符串**: `postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat`
- **表结构**: 已通过 Alembic 迁移创建
- **测试数据**: 已创建 2 个 Agent

### 连接数据库
```bash
PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat
```

## 文件位置

- **应用目录**: `/home/ubuntu/dual-agent-chat/`
- **虚拟环境**: `/home/ubuntu/dual-agent-chat/venv/`
- **日志目录**: `/home/ubuntu/dual-agent-chat/logs/`
- **配置文件**: `/home/ubuntu/dual-agent-chat/.env`
- **Systemd 服务**: `/etc/systemd/system/dual-agent-*.service`
- **Nginx 配置**: `/etc/nginx/sites-available/dual-agent-chat`

## 验证部署

### 1. 检查健康状态
```bash
curl http://129.211.28.211:8080/api/health
```

预期输出：
```json
{
  "status": "ok",
  "services": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "openclaw": {"status": "healthy"},
    "deepseek": {"status": "healthy"}
  }
}
```

### 2. 访问前端
在浏览器中打开：http://129.211.28.211:8080/

### 3. 查看 API 文档
在浏览器中打开：http://129.211.28.211:8080/docs

## 故障排查

### 服务无法启动
```bash
# 查看详细错误
sudo journalctl -u dual-agent-api -n 50
sudo journalctl -u dual-agent-celery -n 50
```

### 无法访问网页
1. 检查防火墙是否开放 8080 端口
2. 检查 Nginx 状态：`sudo systemctl status nginx`
3. 检查 Nginx 错误日志：`sudo tail -f /var/log/nginx/error.log`

### 数据库连接失败
```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 测试连接
PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -c 'SELECT 1;'
```

### Redis 连接失败
```bash
# 检查 Redis 状态
redis-cli ping

# 如果失败，启动 Redis
sudo /usr/bin/redis-server /etc/redis/redis.conf --daemonize yes
```

## 更新应用

如果需要更新代码：

```bash
# 1. 连接服务器
ssh -i ~/.ssh/mingkuan.pem ubuntu@129.211.28.211

# 2. 进入应用目录
cd ~/dual-agent-chat

# 3. 备份当前版本
cp -r ~/dual-agent-chat ~/dual-agent-chat.backup

# 4. 上传新代码（从本地执行）
rsync -avz --exclude 'venv' --exclude '.git' --exclude '__pycache__' \
  -e 'ssh -i ~/.ssh/mingkuan.pem' \
  ./ ubuntu@129.211.28.211:~/dual-agent-chat/

# 5. 重启服务
sudo systemctl restart dual-agent-api dual-agent-celery dual-agent-celery-beat
```

## 安全建议

1. ✅ PostgreSQL 和 Redis 仅监听 localhost
2. ⚠️ 建议修改默认密码
3. ⚠️ 建议配置 HTTPS (使用 Let's Encrypt)
4. ⚠️ 建议限制 8080 端口的访问 IP 范围

## 性能监控

### 系统资源
```bash
# CPU 和内存使用
htop

# 磁盘使用
df -h

# 网络连接
sudo netstat -tlnp
```

### 应用监控
```bash
# 查看进程
ps aux | grep -E '(uvicorn|celery|nginx|postgres|redis)'

# 查看端口
sudo netstat -tlnp | grep -E '(8000|8080|5432|6379)'
```

## 备份建议

### 数据库备份
```bash
# 创建备份
PGPASSWORD='dual_agent_pass' pg_dump -h localhost -U dual_agent_user dual_agent_chat > backup_$(date +%Y%m%d).sql

# 恢复备份
PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat < backup_20260214.sql
```

### 应用备份
```bash
# 备份整个应用目录
tar -czf dual-agent-chat-backup-$(date +%Y%m%d).tar.gz ~/dual-agent-chat
```

## 联系信息

如有问题，请检查：
1. 服务日志文件
2. Nginx 错误日志
3. 系统日志：`sudo journalctl -xe`

---

**部署完成时间**: 2026-02-14
**部署状态**: ✅ 成功
**下一步**: 开放 8080 端口后即可访问
