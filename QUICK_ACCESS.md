# 快速访问指南

## 🌐 所有访问地址

### API服务
- **根路径**: http://localhost:8000/
- **详细API文档**: http://localhost:8000/api-docs ⭐ 新增！
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/api/health

### 前端界面
- **查看界面**: http://localhost:8080/index.html
- **管理面板**: http://localhost:8080/admin.html

## 📖 文档说明

### 1. 详细API文档 (推荐)
**地址**: http://localhost:8000/api-docs

这是专门为开发者准备的详细文档，包含：
- ✅ 完整的接口说明
- ✅ 请求/响应示例
- ✅ 参数详细说明
- ✅ 错误处理指南
- ✅ 多语言使用示例（curl、Python、JavaScript）
- ✅ 完整工作流程演示
- ✅ 常见问题解答

### 2. Swagger UI
**地址**: http://localhost:8000/docs

交互式API文档，可以直接在浏览器中测试API。

### 3. ReDoc
**地址**: http://localhost:8000/redoc

另一种风格的API文档展示。

## 🔑 认证信息

### 测试Token
- Agent 1: `token-agent-1-secret`
- Agent 2: `token-agent-2-secret`

### 获取Token
```bash
python3 verify_database.py
```

## 🚀 快速开始

### 1. 启动所有服务
```bash
./start_services.sh
```

### 2. 检查服务状态
```bash
./check_services.sh
```

### 3. 访问文档
打开浏览器访问: http://localhost:8000/api-docs

### 4. 测试API
```bash
# 健康检查
curl http://localhost:8000/api/health

# 获取活跃话题
curl -H "X-Agent-Token: token-agent-1-secret" \
  http://localhost:8000/api/topic/active
```

## 📱 前端使用

1. 访问 http://localhost:8080/index.html
2. 输入Token: `token-agent-1-secret`
3. 点击"设置Token"
4. 查看实时数据

## 🛑 停止服务
```bash
./stop_services.sh
```

## 📚 更多资源

- **项目README**: [README.md](README.md)
- **API端点列表**: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- **快速开始**: [QUICKSTART.md](QUICKSTART.md)
- **PostgreSQL设置**: [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md)

## 💡 提示

- 详细API文档页面支持平滑滚动导航
- 所有代码示例都可以直接复制使用
- 文档包含完整的错误处理说明
- 支持多种编程语言的示例代码
