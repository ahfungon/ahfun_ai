# MiniMax OpenAI 兼容格式修复

## 重要发现

根据 MiniMax 官方文档（https://platform.minimax.io/docs/api-reference/text-openai-api），MiniMax 提供了 **OpenAI 兼容的 API 格式**！

这意味着我们可以使用标准的 OpenAI API 格式，而不需要使用专用的端点。

## 修复内容

### 1. API 端点更新

#### 修改前（错误）：
- Base URL: `https://api.minimax.chat/v1`
- 端点: `/text/chatcompletion_v2`
- 完整 URL: `https://api.minimax.chat/v1/text/chatcompletion_v2`

#### 修改后（正确）：
- Base URL: `https://api.minimax.io/v1`
- 端点: `/chat/completions`（OpenAI 兼容）
- 完整 URL: `https://api.minimax.io/v1/chat/completions`

### 2. 模型名称更新

#### 修改前（旧版本）：
- 模型名称: `abab6.5-chat`

#### 修改后（最新版本）：
- 模型名称: `MiniMax-M2.5`

### 3. 支持的模型列表

根据官方文档，MiniMax 支持以下模型：

| 模型名称 | 上下文窗口 | 输出速度 | 说明 |
|---------|-----------|---------|------|
| MiniMax-M2.5 | 204,800 | ~60 TPS | 顶尖性能与极致性价比（推荐） |
| MiniMax-M2.5-highspeed | 204,800 | ~100 TPS | M2.5 极速版 |
| MiniMax-M2.1 | 204,800 | ~60 TPS | 强大多语言编程能力 |
| MiniMax-M2.1-highspeed | 204,800 | ~100 TPS | M2.1 极速版 |
| MiniMax-M2 | 204,800 | ~60 TPS | 专为高效编码与 Agent 工作流而生 |

## 修改的文件

### 后端文件

1. **`services/llm_clients/minimax_client.py`**
   - 端点从 `/text/chatcompletion_v2` 改为 `/chat/completions`
   - 默认模型从 `abab6.5-chat` 改为 `MiniMax-M2.5`

2. **`services/system_config_service.py`**
   - API URL 从 `https://api.minimax.chat/v1` 改为 `https://api.minimax.io/v1`
   - 默认模型从 `abab6.5-chat` 改为 `MiniMax-M2.5`

3. **`config/settings.py`**
   - API URL 从 `https://api.minimax.chat/v1` 改为 `https://api.minimax.io/v1`
   - 默认模型从 `abab6.5-chat` 改为 `MiniMax-M2.5`

4. **`services/summary_service.py`**
   - 默认 API URL 和模型更新

5. **`services/message_scoring_service.py`**
   - 默认 API URL 和模型更新

6. **`api/routes.py`**
   - 返回给前端的 API URL 和模型名称更新

### 前端文件

7. **`frontend/admin.html`**
   - 移除了针对 MiniMax 的特殊端点处理
   - 现在 MiniMax 和 DeepSeek 都使用统一的 `/chat/completions` 端点

## 优势

### 1. 统一的 API 格式
- MiniMax 和 DeepSeek 都使用 OpenAI 兼容格式
- 前端代码更简洁，无需区分不同的端点
- 更容易维护和扩展

### 2. 官方支持
- 使用官方推荐的 OpenAI 兼容 API
- 更好的稳定性和兼容性
- 支持 OpenAI SDK 生态系统

### 3. 最新模型
- 使用最新的 MiniMax-M2.5 模型
- 更好的性能和效果
- 支持更大的上下文窗口（204,800 tokens）

## 测试步骤

### 1. 更新数据库配置（重要！）

由于 API URL 和模型名称都变了，需要更新数据库中的配置：

```sql
-- 更新 MiniMax API URL
UPDATE system_config 
SET value = 'https://api.minimax.io/v1' 
WHERE key = 'minimax_api_url';

-- 更新 MiniMax 模型名称
UPDATE system_config 
SET value = 'MiniMax-M2.5' 
WHERE key = 'minimax_model';
```

或者在系统配置页面手动更新：
1. 前往"⚙️ 系统配置"
2. 找到 "MiniMax API URL"，改为 `https://api.minimax.io/v1`
3. 找到 "MiniMax 模型"，改为 `MiniMax-M2.5`
4. 点击"保存配置"

### 2. 重启 Worker（必须！）

```bash
pkill -f celery && python quick_start.py
```

或使用系统配置页面的"重启 Worker"按钮。

### 3. 刷新浏览器

强制刷新：`Ctrl+F5` (Windows) 或 `Cmd+Shift+R` (Mac)

### 4. 测试 MiniMax 智能体

1. 进入"智能体模拟器"
2. 添加使用 "MiniMax 调用" 的智能体
3. 启动并观察日志

### 预期结果

```
✅ MiniMax Agent 启动成功
💬 MiniMax Agent 发送消息: ...
✅ MiniMax Agent 消息发送成功
🤖 MiniMax Agent 使用 MINIMAX 生成回复
```

### 5. 验证 API 调用

打开浏览器开发者工具（F12），Network 标签：
- 请求 URL: `https://api.minimax.io/v1/chat/completions`
- 状态码: `200`
- 请求体中的 model: `MiniMax-M2.5`

## API 格式对比

### OpenAI 兼容格式（现在使用）

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.minimax.io/v1",
    api_key="YOUR_API_KEY"
)

response = client.chat.completions.create(
    model="MiniMax-M2.5",
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)
```

### 原生格式（已弃用）

```python
import requests

response = requests.post(
    "https://api.minimax.chat/v1/text/chatcompletion_v2",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "abab6.5-chat",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
```

## 常见问题

### Q1: 为什么要改用 OpenAI 兼容格式？

**答**：
1. 官方推荐的标准格式
2. 更好的生态系统支持
3. 与 DeepSeek 使用相同的格式，代码更统一
4. 支持最新的模型

### Q2: 旧的 API Key 还能用吗？

**答**：可以！API Key 不需要更改，只需要更新 API URL 和模型名称。

### Q3: 需要重新配置吗？

**答**：需要更新两个配置项：
- MiniMax API URL: `https://api.minimax.io/v1`
- MiniMax 模型: `MiniMax-M2.5`

### Q4: 如果想使用极速版怎么办？

**答**：在系统配置中将模型名称改为 `MiniMax-M2.5-highspeed` 即可。

## 参考文档

- [MiniMax OpenAI 兼容 API 文档](https://platform.minimax.io/docs/api-reference/text-openai-api)
- [MiniMax 文本生成指南](https://platform.minimaxi.com/docs/guides/text-generation)
- [MiniMax 模型概览](https://platform.minimax.io/docs/api-reference/api-overview)

## 注意事项

1. **必须更新数据库配置**：API URL 和模型名称都需要更新
2. **必须重启 Worker**：后端代码修改需要重启才能生效
3. **必须刷新浏览器**：前端代码修改需要刷新才能生效
4. **检查 API Key**：确保使用的是 MiniMax 的有效 API Key
