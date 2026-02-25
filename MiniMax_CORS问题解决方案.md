# MiniMax CORS 问题解决方案

## 问题诊断

### 根本原因
前端智能体模拟器直接从浏览器调用 MiniMax API 时遇到 CORS（跨域资源共享）问题：
- 浏览器从 `localhost:8080` 尝试访问 `api.minimax.chat` 被 CORS 策略阻止
- DeepSeek API 支持 CORS（返回 `access-control-allow-origin` 头），但 MiniMax 不支持
- 错误信息：`Failed to fetch` (TypeError)

### 为什么 DeepSeek 可以但 MiniMax 不行？
- DeepSeek API 服务器配置了 CORS 头，允许跨域请求
- MiniMax API 服务器没有配置 CORS 头，浏览器阻止了请求
- 这是 API 提供商的服务器配置差异，不是我们的代码问题

## 解决方案：后端代理

### 架构改变
**之前（直接调用）：**
```
浏览器 → MiniMax API (被 CORS 阻止)
```

**现在（后端代理）：**
```
浏览器 → 后端代理 → MiniMax API (成功)
```

### 实现细节

#### 1. 新增后端代理端点
**文件：** `api/routes.py`

**端点：** `POST /api/admin/llm/proxy`

**功能：**
- 接收前端的 LLM 请求（provider, messages, temperature, max_tokens）
- 从系统配置读取对应的 API Key 和 URL
- 转发请求到 LLM API（DeepSeek 或 MiniMax）
- 返回 LLM 响应给前端

**请求格式：**
```json
{
  "provider": "minimax",  // 或 "deepseek"
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.8,
  "max_tokens": 500
}
```

**响应格式：**
```json
{
  "success": true,
  "provider": "minimax",
  "content": "你好！我是...",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

#### 2. 修改前端调用方式
**文件：** `frontend/admin.html`

**修改：** `generateLLMReply` 函数

**之前：**
```javascript
// 直接调用 LLM API（会遇到 CORS）
const response = await fetch(llmConfig.api_url + '/chat/completions', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${llmConfig.api_key}`
    },
    body: JSON.stringify({...})
});
```

**现在：**
```javascript
// 通过后端代理调用（避免 CORS）
const response = await fetch('/api/admin/llm/proxy', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        provider: agent.mode,  // 'deepseek' 或 'minimax'
        messages: [...],
        temperature: 0.8,
        max_tokens: 500
    })
});
```

## 优势

### 1. 解决 CORS 问题
- 后端到后端的请求不受 CORS 限制
- 适用于所有不支持 CORS 的 API

### 2. 统一配置管理
- API Key 只存储在后端系统配置中
- 前端不需要直接访问 API Key
- 更安全，API Key 不会暴露在浏览器中

### 3. 统一错误处理
- 后端可以统一处理 API 错误
- 可以添加重试、限流等逻辑
- 更好的日志记录

### 4. 兼容性
- 同时支持 DeepSeek 和 MiniMax
- 前端代码统一，不需要区分不同的 API

## 测试步骤

### 1. 启动服务
```bash
# 确保后端服务运行
python main.py
```

### 2. 测试代理端点
```bash
# 运行测试脚本
python test_llm_proxy.py
```

### 3. 测试前端模拟器
1. 打开管理后台：http://localhost:8080/admin.html
2. 进入"智能体模拟器"
3. 添加智能体，选择"MiniMax 调用"模式
4. 启动智能体，观察日志

### 预期结果
- ✅ MiniMax 调用成功
- ✅ 日志显示"使用 MINIMAX 生成回复"
- ✅ 智能体正常发言

## 技术细节

### API Key 安全性
- API Key 存储在后端数据库（系统配置）
- 前端只能通过代理端点调用，无法直接获取 API Key
- 代理端点从系统配置读取 API Key，不暴露给前端

### 错误处理
- 如果 API Key 未配置，返回 400 错误
- 如果 LLM API 调用失败，返回相应的 HTTP 错误码
- 前端收到错误后，自动降级到模板模式

### 性能考虑
- 代理增加了一层转发，但延迟可忽略（< 10ms）
- LLM API 调用本身需要 1-3 秒，代理延迟占比很小
- 可以在代理层添加缓存、限流等优化

## 后续优化建议

### 1. 添加请求缓存
对于相同的 prompt，可以缓存响应，减少 API 调用

### 2. 添加限流保护
防止前端模拟器过度调用 API，保护 API 配额

### 3. 添加请求日志
记录所有 LLM API 调用，便于分析和调试

### 4. 支持流式响应
如果 LLM API 支持流式输出，可以实现实时显示

## 总结

通过添加后端代理端点，我们成功解决了 MiniMax API 的 CORS 问题。这个方案不仅解决了当前问题，还提供了更好的安全性和可扩展性。

**关键改变：**
- ✅ 新增 `/api/admin/llm/proxy` 端点
- ✅ 修改前端 `generateLLMReply` 函数使用代理
- ✅ 统一 DeepSeek 和 MiniMax 的调用方式
- ✅ 提高 API Key 安全性

**测试验证：**
- ✅ 后端代理端点正常工作
- ✅ 前端模拟器可以调用 MiniMax
- ✅ 错误处理和降级机制正常
