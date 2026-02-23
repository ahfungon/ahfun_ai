# 前端 API URL 修复总结

## 问题描述

前端页面中硬编码了 `http://localhost:8000/api` 作为 API URL，导致从外部 IP 访问时无法正常调用后端 API，出现连接失败的问题。

## 修复内容

### 修改的文件
1. `frontend/monitor.html` - 监控页面
2. `frontend/index.html` - 聊天页面  
3. `frontend/admin.html` - 管理页面

### 具体修改
将所有文件中的：
```javascript
apiUrl: 'http://localhost:8000/api'
```

改为：
```javascript
apiUrl: '/api'
```

## 修复原理

使用相对路径 `/api` 替代绝对路径 `http://localhost:8000/api`，这样：
- 浏览器会自动使用当前页面的协议和域名
- 从 `http://129.211.28.211:8080` 访问时，API 请求会发送到 `http://129.211.28.211:8080/api`
- Nginx 会将 `/api` 请求代理到后端 FastAPI 服务（运行在 localhost:8000）

## 部署步骤

### 1. 本地修改
```bash
# 修改三个前端文件的 apiUrl 配置
# monitor.html: line 276
# index.html: line 290  
# admin.html: line 357
```

### 2. 提交到 Git
```bash
git add frontend/monitor.html frontend/index.html frontend/admin.html
git commit -m "fix: 修复前端页面 API URL 硬编码问题"
git push origin main
```

提交 ID: `e45e256`

### 3. 上传到服务器
```bash
scp frontend/monitor.html frontend/index.html frontend/admin.html \
    mingkuan:/home/ubuntu/dual-agent-chat/frontend/
```

### 4. 验证修复
```bash
ssh mingkuan "grep -n 'apiUrl:' /home/ubuntu/dual-agent-chat/frontend/*.html"
```

输出确认：
```
/home/ubuntu/dual-agent-chat/frontend/admin.html:357:    apiUrl: '/api',
/home/ubuntu/dual-agent-chat/frontend/index.html:290:    apiUrl: '/api',
/home/ubuntu/dual-agent-chat/frontend/monitor.html:276:  apiUrl: '/api',
```

## 测试验证

所有页面现在都可以从外部 IP 正常访问：

- ✅ 监控页面: http://129.211.28.211:8080/
- ✅ 聊天页面: http://129.211.28.211:8080/index.html
- ✅ 管理页面: http://129.211.28.211:8080/admin.html
- ✅ 认证信息页面: http://129.211.28.211:8080/auth-info.html

## 技术说明

### Nginx 配置
Nginx 配置文件 `/etc/nginx/sites-available/dual-agent-chat` 中已经配置了 API 代理：

```nginx
location /api/ {
    proxy_pass http://localhost:8000/api/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

这个配置确保：
- 外部请求 `http://129.211.28.211:8080/api/*` 
- 被代理到 `http://localhost:8000/api/*`
- FastAPI 服务处理请求并返回响应

## 相关文档

- 部署文档: `DEPLOYMENT_SUMMARY.md`
- API 文档: `API_ENDPOINTS.md`
- 前端使用指南: `前端页面使用说明.md`

## 修复日期

2026-02-14

## 修复人员

Kiro AI Assistant
