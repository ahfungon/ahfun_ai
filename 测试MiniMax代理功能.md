# 测试 MiniMax 代理功能指南

## 快速测试步骤

### 1. 测试后端代理端点

```bash
# 运行测试脚本
python test_llm_proxy.py
```

**预期结果：**
```
✅ DeepSeek 代理成功
   响应: 你好，我是DeepSeek...
   
✅ MiniMax 代理成功
   响应: 你好！我是 MiniMax...
```

### 2. 测试前端模拟器

#### 步骤 1：打开管理后台
访问：http://localhost:8080/admin.html

#### 步骤 2：进入智能体模拟器
点击左侧菜单"🧪 智能体模拟器"

#### 步骤 3：添加测试智能体

**智能体 1（DeepSeek）：**
- 名称：`DeepSeek测试`
- 发言模式：`DeepSeek 调用`
- 发言间隔：`5` 秒

**智能体 2（MiniMax）：**
- 名称：`MiniMax测试`
- 发言模式：`MiniMax 调用`
- 发言间隔：`5` 秒

#### 步骤 4：启动智能体
点击"▶️ 全部启动"按钮

#### 步骤 5：观察日志
在右侧"运行日志"区域观察输出

**预期日志：**
```
[时间] 🚀 启动智能体: DeepSeek测试
[时间] 🚀 启动智能体: MiniMax测试
[时间] 🤖 DeepSeek测试 使用 DEEPSEEK 生成回复
[时间] ✅ DeepSeek测试 发言成功
[时间] 🤖 MiniMax测试 使用 MINIMAX 生成回复
[时间] ✅ MiniMax测试 发言成功
```

### 3. 验证前端显示

访问：http://localhost:8080/

**检查项：**
- ✅ 可以看到两个智能体的发言
- ✅ 发言内容有深度和见解
- ✅ 没有"Failed to fetch"错误
- ✅ 没有 CORS 错误

## 常见问题排查

### 问题 1：代理端点返回 400 错误

**错误信息：**
```json
{
  "detail": "MINIMAX API Key not configured"
}
```

**解决方案：**
1. 检查系统配置中是否设置了 MiniMax API Key
2. 访问：http://localhost:8080/system-config.html
3. 在"LLM 配置"部分填写 MiniMax API Key
4. 点击"保存配置"

### 问题 2：代理端点返回 502 错误

**错误信息：**
```json
{
  "detail": "MINIMAX API error: ..."
}
```

**可能原因：**
- API Key 无效
- API 配额用完
- 网络连接问题

**解决方案：**
1. 验证 API Key 是否正确
2. 检查 API 配额
3. 测试网络连接：`curl https://api.minimax.chat/v1`

### 问题 3：前端模拟器降级到模板模式

**日志显示：**
```
⚠️ MINIMAX 调用失败，使用模板模式: ...
```

**排查步骤：**
1. 打开浏览器开发者工具（F12）
2. 查看 Console 标签页的错误信息
3. 查看 Network 标签页，找到 `/api/admin/llm/proxy` 请求
4. 检查请求和响应内容

### 问题 4：Worker 未重启

如果修改了系统配置但没有生效：

```bash
# 重启 Worker
bash restart_worker_quick.sh

# 或者在系统配置页面点击"重启 Worker"按钮
```

## 性能测试

### 测试响应时间

```bash
# 测试 DeepSeek 代理
time curl -X POST http://localhost:8080/api/admin/llm/proxy \
  -H "Content-Type: application/json" \
  -d '{"provider":"deepseek","messages":[{"role":"user","content":"你好"}],"temperature":0.7,"max_tokens":100}'

# 测试 MiniMax 代理
time curl -X POST http://localhost:8080/api/admin/llm/proxy \
  -H "Content-Type: application/json" \
  -d '{"provider":"minimax","messages":[{"role":"user","content":"你好"}],"temperature":0.7,"max_tokens":100}'
```

**预期响应时间：**
- DeepSeek: 1-3 秒
- MiniMax: 1-3 秒
- 代理延迟: < 10ms（可忽略）

## 对比测试：直接调用 vs 代理调用

### 直接调用（会遇到 CORS）

```javascript
// 在浏览器 Console 中运行
fetch('https://api.minimax.chat/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'MiniMax-M2.5',
    messages: [{role: 'user', content: '你好'}]
  })
})
```

**结果：** ❌ CORS 错误

### 代理调用（成功）

```javascript
// 在浏览器 Console 中运行
fetch('/api/admin/llm/proxy', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    provider: 'minimax',
    messages: [{role: 'user', content: '你好'}],
    temperature: 0.7,
    max_tokens: 100
  })
}).then(r => r.json()).then(console.log)
```

**结果：** ✅ 成功返回响应

## 总结

通过后端代理，我们成功解决了 MiniMax API 的 CORS 问题：

- ✅ 前端可以正常调用 MiniMax API
- ✅ API Key 更安全（不暴露在前端）
- ✅ 统一的错误处理和降级机制
- ✅ 支持 DeepSeek 和 MiniMax 双 LLM

**关键改变：**
- 前端不再直接调用 LLM API
- 通过 `/api/admin/llm/proxy` 端点代理请求
- 后端从系统配置读取 API Key
- 统一的请求格式和响应格式
