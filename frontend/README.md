# 双Agent对话平台 - 前端界面

简洁的单页面应用，用于查看和监控双Agent对话系统。

## 功能特性

- 📊 实时显示活跃话题信息
- 💬 查看对话消息历史
- 🔄 自动刷新（每5秒）
- 🎨 响应式设计
- 🔐 Token认证

## 快速开始

### 方式一：直接打开HTML文件

1. 确保后端API服务正在运行（默认 http://localhost:8000）
2. 直接在浏览器中打开 `index.html` 文件
3. 输入Agent Token并点击"设置Token"
4. 数据将自动加载和刷新

### 方式二：使用本地服务器

如果遇到CORS问题，可以使用本地服务器：

```bash
# 使用Python
cd frontend
python -m http.server 8080

# 或使用Node.js
npx http-server -p 8080
```

然后访问 http://localhost:8080

## 获取Agent Token

Agent Token在数据库中的 `agents` 表中：

```sql
SELECT id, name, token FROM agents;
```

或使用提供的脚本：

```bash
cd ..
python verify_database.py
```

## 界面说明

### 左侧面板 - 对话消息
- 显示当前话题的所有消息
- Agent 1 消息显示为青色背景
- Agent 2 消息显示为橙色背景
- 自动滚动到最新消息

### 右侧面板 - 话题信息
- 话题ID和标题
- 当前状态（活跃/等待关闭/已关闭）
- Token计数和结束评分
- LLM建议和提示
- 话题摘要（如果有）
- 关闭状态（如果在closing_pending状态）

## 自定义配置

如果API服务运行在不同的地址，修改 `index.html` 中的 `apiUrl`：

```javascript
const app = {
    apiUrl: 'http://your-api-host:port/api',
    // ...
};
```

## 浏览器兼容性

支持所有现代浏览器：
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## 注意事项

1. 确保后端API已启用CORS（已在main.py中配置）
2. Token会保存在浏览器的localStorage中
3. 自动刷新间隔为5秒，可在代码中调整
4. 消息默认显示最近50条，可通过API参数调整
