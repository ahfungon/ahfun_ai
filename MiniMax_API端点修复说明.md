# MiniMax API 端点修复说明

## 问题描述

用户报告 MiniMax 调用失败，日志显示：
```
[18:32:36] ⚠️ MINIMAX 调用失败，使用模板模式: Failed to fetch
```

而 DeepSeek 调用正常。

## 根本原因

MiniMax 使用的 API 端点与 OpenAI 兼容的端点不同：

- ❌ 错误端点：`https://api.minimax.chat/v1/chat/completions`（OpenAI 格式）
- ✅ 正确端点：`https://api.minimax.chat/v1/text/chatcompletion_v2`（MiniMax 专用）

之前的代码错误地使用了 OpenAI 兼容的端点格式，导致 MiniMax API 调用失败。

## 解决方案

### 1. 修复后端 MiniMax 客户端 (`services/llm_clients/minimax_client.py`)

修改了两处 API 调用：

#### 修改 1：`_make_request` 方法（用于对话总结）

```python
# 修改前
response = requests.post(
    f"{self.api_url}/chat/completions",
    headers=headers,
    json=payload,
    timeout=self.timeout
)

# 修改后
response = requests.post(
    f"{self.api_url}/text/chatcompletion_v2",
    headers=headers,
    json=payload,
    timeout=self.timeout
)
```

#### 修改 2：`evaluate_message_relevance` 方法（用于消息评分）

```python
# 修改前
response = requests.post(
    f"{self.api_url}/chat/completions",
    headers=headers,
    json=payload,
    timeout=self.timeout
)

# 修改后
response = requests.post(
    f"{self.api_url}/text/chatcompletion_v2",
    headers=headers,
    json=payload,
    timeout=self.timeout
)
```

### 2. 修复前端模拟器 (`frontend/admin.html`)

在 `generateLLMReply` 方法中，根据 LLM 类型选择不同的端点：

```javascript
// 调用 LLM API
let apiEndpoint;
if (agent.mode === 'minimax') {
    // MiniMax 使用不同的端点
    apiEndpoint = llmConfig.api_url + '/text/chatcompletion_v2';
} else {
    // DeepSeek 使用标准的 OpenAI 兼容端点
    apiEndpoint = llmConfig.api_url + '/chat/completions';
}

const response = await fetch(apiEndpoint, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${llmConfig.api_key}`
    },
    body: JSON.stringify({
        model: llmConfig.model,
        messages: [
            { role: 'user', content: prompt }
        ],
        temperature: 0.8,
        max_tokens: 500
    })
});
```

## API 端点对比

| LLM 提供商 | 基础 URL | 端点路径 | 完整 URL |
|-----------|---------|---------|----------|
| DeepSeek | `https://api.deepseek.com/v1` | `/chat/completions` | `https://api.deepseek.com/v1/chat/completions` |
| MiniMax | `https://api.minimax.chat/v1` | `/text/chatcompletion_v2` | `https://api.minimax.chat/v1/text/chatcompletion_v2` |

## 影响范围

此修复影响以下功能：

1. **后端服务**：
   - 对话总结（使用 MiniMax 时）
   - 消息评分（使用 MiniMax 时）

2. **前端模拟器**：
   - 智能体使用 MiniMax 生成回复

## 测试步骤

### 1. 重启 Worker（后端修复生效）

```bash
pkill -f celery && python quick_start.py
```

或使用系统配置页面的"重启 Worker"按钮。

### 2. 刷新前端页面（前端修复生效）

刷新管理后台页面（Ctrl+F5 或 Cmd+Shift+R）。

### 3. 测试前端模拟器

1. 进入"智能体模拟器"
2. 添加一个使用 MiniMax 的智能体
3. 启动智能体
4. 观察日志，应该看到：
   ```
   ✅ MINIMAX Agent 启动成功
   💬 MINIMAX Agent 发送消息: ...
   ✅ MINIMAX Agent 消息发送成功
   🤖 MINIMAX Agent 使用 MINIMAX 生成回复
   ```

### 4. 测试后端服务

触发一次对话总结（发送足够多的消息达到 token 阈值），检查日志：

```bash
tail -f logs/worker.log
```

应该看到 MiniMax 调用成功的日志。

## 验证成功的标志

✅ 前端模拟器中 MiniMax 智能体不再显示"调用失败"
✅ 日志中显示"使用 MINIMAX 生成回复"
✅ 后端 Worker 日志中 MiniMax API 调用成功
✅ 浏览器 Network 标签中可以看到对 `/text/chatcompletion_v2` 的成功请求

## 注意事项

1. **API 兼容性**：MiniMax 不使用 OpenAI 兼容的 API 格式，需要使用专用端点
2. **模型名称**：确认使用的模型名称 `abab6.5-chat` 是否正确
3. **API Key 格式**：MiniMax 的 API Key 格式与 DeepSeek 不同（JWT 格式）
4. **响应格式**：虽然端点不同，但响应格式应该兼容 OpenAI 格式

## 相关文档

- MiniMax 官方 API 文档：https://api.minimax.chat/document/guides/chat-model/V2
- 系统配置说明：`系统配置管理功能说明.md`
- 测试指南：`测试多LLM支持指南.md`

## 修改的文件

1. `services/llm_clients/minimax_client.py` - 修复后端 API 端点（2处）
2. `frontend/admin.html` - 修复前端 API 端点（1处）
