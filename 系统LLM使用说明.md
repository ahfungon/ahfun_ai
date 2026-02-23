# 系统 LLM 使用说明

## 概述

本系统在多个场景使用 LLM（大语言模型）来提供智能功能。目前所有后端服务都统一使用 **DeepSeek API**。

## 🎯 LLM 使用场景

系统中有 **3 个主要场景** 使用 LLM：

### 1. 消息评分系统 ⭐

**位置**: `services/message_scoring_service.py`

**用途**: 评估每条消息与话题的相关性

**使用的 LLM**: DeepSeek API

**触发时机**: 
- 每条消息发送后自动触发（异步）
- 通过 Celery Worker 执行

**评分维度**:
- 主题相关性 (40%)
- 内容质量 (30%)
- 讨论推进 (30%)

**配置**:
```python
# services/message_scoring_service.py
self.deepseek_client = DeepSeekClient(
    api_key=settings.deepseek_api_key,
    api_url=settings.deepseek_api_url
)
```

**API 调用**:
```python
result = self.deepseek_client.evaluate_message_relevance(prompt)
```

---

### 2. 对话总结系统 📝

**位置**: `services/summary_service.py`

**用途**: 当 token 达到阈值时生成对话总结

**使用的 LLM**: DeepSeek API ✅

**触发时机**:
- Token 计数达到 `SUMMARY_THRESHOLD`（默认 8000）
- 自动触发总结生成

**功能**:
- 生成累积式总结（包含历史总结 + 新消息）
- 提供 LLM 建议（continue/close）
- 计算结束评分（0-100）

**配置**:
```python
# services/summary_service.py
self.deepseek_client = DeepSeekClient(
    api_key=settings.deepseek_api_key,
    api_url=settings.deepseek_api_url,
    timeout=30,
    max_retries=3,
    retry_delays=[1, 2, 4]
)
```

**API 调用**:
```python
llm_response = self.deepseek_client.generate_summary(
    prompt=prompt,
    temperature=0.3,
    max_tokens=2000
)
```

---

### 3. 模拟器对话生成 🤖

**位置**: `simulation_test/enhanced_simulator.py`

**用途**: 模拟智能体生成对话内容（测试用）

**使用的 LLM**: DeepSeek（推荐）或 OpenAI

**触发时机**:
- 手动启用（`--use-llm` 参数）
- 仅在测试时使用

**配置**:
- 优先使用环境变量 `DEEPSEEK_API_KEY`
- 其次使用 `OPENAI_API_KEY`
- 最后使用 `config.yaml` 中的配置

**API 调用**:
```python
content, tokens = llm_backend.generate_response(
    system_prompt,
    conversation_history,
    temperature=0.7
)
```

---

## 📊 LLM 使用对比

| 场景 | 服务 | LLM | 触发方式 | 必需性 | 配置位置 |
|------|------|-----|---------|--------|---------|
| **消息评分** | 后端 | DeepSeek | 自动（每条消息） | ✅ 必需 | `.env` |
| **对话总结** | 后端 | DeepSeek | 自动（达到阈值） | ✅ 必需 | `.env` |
| **对话生成** | 测试 | DeepSeek/OpenAI | 手动（--use-llm） | ❌ 可选 | 环境变量/config.yaml |

---

## 🔧 配置方法

### 后端服务配置（评分 + 总结）

**配置文件**: `.env`

```bash
# DeepSeek API 配置（用于评分和总结）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
DEEPSEEK_API_URL=https://api.deepseek.com/v1

# 总结阈值配置
SUMMARY_THRESHOLD=8000
```

**代码读取**:
```python
# config/settings.py
deepseek_api_key: str = Field(..., env="DEEPSEEK_API_KEY")
deepseek_api_url: str = Field(
    default="https://api.deepseek.com/v1",
    env="DEEPSEEK_API_URL"
)
```

### 模拟器配置（测试）

**方法 1: 环境变量（推荐）**

```bash
# 使用 DeepSeek（与后端一致）
export DEEPSEEK_API_KEY="your-key"

# 或使用 OpenAI
export OPENAI_API_KEY="your-key"
```

**方法 2: 配置文件**

编辑 `simulation_test/config.yaml`:
```yaml
llm:
  api_key: "your-key"
  api_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"
```

---

## 🔍 验证配置

### 验证后端配置

```bash
# 检查 .env 文件
cat .env | grep DEEPSEEK

# 应该看到：
# DEEPSEEK_API_KEY=sk-xxxxx
# DEEPSEEK_API_URL=https://api.deepseek.com/v1
```

### 验证模拟器配置

```bash
cd simulation_test
make verify
```

输出示例：
```
✅ 将使用: DEEPSEEK_API_KEY 环境变量
   API URL: https://api.deepseek.com/v1
   Model: deepseek-chat
   优先级: 最高 (1)
```

---

## 📈 API 调用流程

### 1. 消息评分流程

```
用户发送消息
    ↓
POST /api/message
    ↓
MessageService.create_message()
    ↓
事务提交后触发
    ↓
evaluate_message_relevance.delay() (Celery 异步任务)
    ↓
Celery Worker 执行
    ↓
MessageScoringService.evaluate_message()
    ↓
DeepSeekClient.evaluate_message_relevance()
    ↓
调用 DeepSeek API
    ↓
保存评分到数据库
```

### 2. 对话总结流程

```
消息累积
    ↓
Token 计数达到阈值 (8000)
    ↓
触发总结任务
    ↓
SummaryService.generate_summary()
    ↓
构建总结提示词
    ↓
DeepSeekClient.generate_summary()
    ↓
调用 DeepSeek API
    ↓
解析响应（summary + suggestion + end_score）
    ↓
更新话题总结
    ↓
保存总结历史
    ↓
重置 Token 计数
```

### 3. 模拟器对话生成流程

```
启动模拟器 (--use-llm)
    ↓
创建 LLMBackend 实例
    ↓
每轮对话
    ↓
Agent.generate_response_with_llm()
    ↓
构建系统提示词（包含评分反馈）
    ↓
LLMBackend.generate_response()
    ↓
调用 DeepSeek/OpenAI API
    ↓
返回生成的对话内容
```

---

## 💰 成本考虑

### 后端服务（生产环境）

**消息评分**:
- 每条消息: 1 次 API 调用
- Token 消耗: ~500-1000 tokens/次
- 频率: 每条消息

**对话总结**:
- 触发条件: 每 8000 tokens
- Token 消耗: ~1000-2000 tokens/次
- 频率: 较低

**估算**:
- 假设每天 1000 条消息
- 评分: 1000 次调用
- 总结: ~10 次调用
- 总计: ~1010 次调用/天

### 测试环境（模拟器）

**对话生成**:
- 每条消息: 1 次 API 调用
- Token 消耗: ~300-500 tokens/次
- 频率: 仅测试时

**建议**:
- 开发测试时可以不使用 LLM（节省成本）
- 只在需要测试评分系统时才启用 `--use-llm`

---

## 🛠️ DeepSeek 客户端

### 客户端位置

`services/llm_clients/deepseek_client.py`

### 主要功能

```python
class DeepSeekClient(BaseLLMClient):
    """DeepSeek API 客户端"""
    
    def generate_summary(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """生成对话总结"""
        
    def evaluate_message_relevance(
        self,
        prompt: str,
        temperature: float = 0.3
    ) -> Optional[Dict[str, Any]]:
        """评估消息相关性"""
```

### 特性

- ✅ 自动重试机制（最多 3 次）
- ✅ 指数退避策略（1s, 2s, 4s）
- ✅ 超时控制（30 秒）
- ✅ 错误处理和日志记录
- ✅ 响应验证和清洗

---

## 🔄 切换 LLM 提供商

### 当前状态

- ✅ 评分系统: DeepSeek
- ✅ 总结系统: DeepSeek
- ⚙️ 模拟器: DeepSeek（推荐）或 OpenAI

### 如果需要切换

#### 1. 切换评分系统

修改 `services/message_scoring_service.py`:
```python
# 从 DeepSeek 切换到其他 LLM
from services.llm_clients.other_client import OtherClient

self.llm_client = OtherClient(
    api_key=settings.other_api_key,
    api_url=settings.other_api_url
)
```

#### 2. 切换总结系统

修改 `services/summary_service.py`:
```python
# 从 DeepSeek 切换到其他 LLM
from services.llm_clients.other_client import OtherClient

self.llm_client = OtherClient(
    api_key=settings.other_api_key,
    api_url=settings.other_api_url
)
```

#### 3. 切换模拟器

修改环境变量或 `config.yaml`:
```bash
export OTHER_API_KEY="your-key"
```

---

## 📝 总结

### 统一使用 DeepSeek

系统后端服务（评分 + 总结）统一使用 DeepSeek API：

- ✅ **一致性**: 所有后端服务使用同一个 API
- ✅ **简化配置**: 只需配置一个 API 密钥
- ✅ **成本优化**: DeepSeek 性价比高
- ✅ **易于维护**: 统一的客户端和错误处理

### 配置位置

| 场景 | 配置文件 | 环境变量 |
|------|---------|---------|
| 评分系统 | `.env` | `DEEPSEEK_API_KEY` |
| 总结系统 | `.env` | `DEEPSEEK_API_KEY` |
| 模拟器 | `config.yaml` 或环境变量 | `DEEPSEEK_API_KEY` |

### 快速检查

```bash
# 检查后端配置
cat .env | grep DEEPSEEK

# 检查模拟器配置
cd simulation_test && make verify

# 测试评分系统
# 发送一条消息，查看是否有评分

# 测试总结系统
# 发送足够多的消息（达到 8000 tokens），查看是否生成总结

# 测试模拟器
export DEEPSEEK_API_KEY="your-key"
cd simulation_test && make test-llm
```

---

## 🎉 结论

**是的，当 token 达到阈值时调用大模型进行总结，也是用的 DeepSeek！** ✅

系统中所有后端 LLM 功能（评分 + 总结）都统一使用 DeepSeek API，配置在 `.env` 文件中。
