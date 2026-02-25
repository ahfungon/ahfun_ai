# MiniMax 代理快速参考

## 一句话总结
通过后端代理端点 `/api/admin/llm/proxy` 解决 MiniMax API 的 CORS 跨域问题。

---

## 快速测试

### 1. 测试后端代理
```bash
python test_llm_proxy.py
```

### 2. 测试前端模拟器
1. 访问：http://localhost:8080/admin.html
2. 进入"智能体模拟器"
3. 添加智能体，选择"MiniMax 调用"
4. 启动智能体，观察日志

---

## API 端点

### 代理端点
```
POST /api/admin/llm/proxy
```

### 请求示例
```json
{
  "provider": "minimax",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.8,
  "max_tokens": 500
}
```

### 响应示例
```json
{
  "success": true,
  "provider": "minimax",
  "content": "你好！我是...",
  "usage": {"total_tokens": 125}
}
```

---

## 前端调用示例

```javascript
// 通过代理调用 MiniMax
const response = await fetch('/api/admin/llm/proxy', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        provider: 'minimax',  // 或 'deepseek'
        messages: [
            {role: 'user', content: '你好'}
        ],
        temperature: 0.8,
        max_tokens: 500
    })
});

const data = await response.json();
console.log(data.content);  // LLM 生成的内容
```

---

## 配置要求

### 系统配置
访问：http://localhost:8080/system-config.html

需要配置：
- **MiniMax API Key**: `sk-cp-cjKQ...`
- **MiniMax API URL**: `https://api.minimax.chat/v1`
- **MiniMax 模型**: `MiniMax-M2.5`

### 重启 Worker
修改配置后需要重启：
```bash
bash restart_worker_quick.sh
```
或在系统配置页面点击"重启 Worker"按钮

---

## 常见错误

### 错误 1：API Key 未配置
```json
{"detail": "MINIMAX API Key not configured"}
```
**解决：** 在系统配置中设置 MiniMax API Key

### 错误 2：API 调用失败
```json
{"detail": "MINIMAX API error: ..."}
```
**解决：** 检查 API Key 是否正确，检查网络连接

### 错误 3：前端降级到模板模式
```
⚠️ MINIMAX 调用失败，使用模板模式
```
**解决：** 打开浏览器开发者工具（F12），查看 Network 标签页的错误信息

---

## 架构对比

### 之前（失败）
```
浏览器 → MiniMax API ❌ CORS 错误
```

### 现在（成功）
```
浏览器 → 后端代理 → MiniMax API ✅ 成功
```

---

## 优势

- ✅ 解决 CORS 跨域问题
- ✅ API Key 更安全（不暴露在前端）
- ✅ 统一配置管理
- ✅ 统一错误处理
- ✅ 性能影响小（< 10ms）

---

## 相关文件

### 修改的文件
- `api/routes.py` - 新增代理端点
- `frontend/admin.html` - 修改调用方式

### 测试文件
- `test_llm_proxy.py` - 测试脚本

### 文档
- `MiniMax_CORS问题完整解决报告.md` - 完整报告
- `MiniMax_CORS问题解决方案.md` - 解决方案
- `测试MiniMax代理功能.md` - 测试指南
- `CORS问题对比图.md` - 可视化对比
- `API_ENDPOINTS.md` - API 文档

---

## 支持的 LLM 提供商

| 提供商 | Provider 值 | API URL | 模型 |
|--------|------------|---------|------|
| DeepSeek | `deepseek` | `https://api.deepseek.com/v1` | `deepseek-chat` |
| MiniMax | `minimax` | `https://api.minimax.chat/v1` | `MiniMax-M2.5` |

---

## 快速命令

```bash
# 测试代理端点
python test_llm_proxy.py

# 重启 Worker
bash restart_worker_quick.sh

# 启动服务
python main.py

# 查看日志
tail -f logs/worker.log
```

---

## 联系方式

如有问题，请查看：
- 完整报告：`MiniMax_CORS问题完整解决报告.md`
- API 文档：`API_ENDPOINTS.md`
- 测试指南：`测试MiniMax代理功能.md`
