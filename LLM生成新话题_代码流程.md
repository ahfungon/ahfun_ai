# LLM 生成新话题 - 代码流程详解

## 📍 代码位置总览

| 文件 | 功能 | 关键方法/函数 |
|------|------|--------------|
| `services/topic_service.py` | 话题服务核心逻辑 | `generate_topic_with_llm()`, `record_close_request()` |
| `workers/tasks.py` | Celery 异步任务 | `generate_new_topic()` |
| `services/llm_clients/deepseek_client.py` | DeepSeek API 客户端 | `DeepSeekClient` |
| `config/settings.py` | 配置管理 | `deepseek_api_key`, `deepseek_api_url` |

---

## 🔄 完整流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. 话题关闭触发                               │
│                                                                 │
│  Agent A 请求关闭 → Agent B 同意关闭 → 话题状态变为 "closed"    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              2. 触发异步任务 (services/topic_service.py)         │
│                                                                 │
│  record_close_request() 方法中：                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ from workers.tasks import generate_new_topic             │  │
│  │ generate_new_topic.apply_async(                          │  │
│  │     args=[agent_id],                                     │  │
│  │     countdown=2  # 延迟 2 秒执行                          │  │
│  │ )                                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              3. Celery 任务执行 (workers/tasks.py)              │
│                                                                 │
│  @celery_app.task(name="workers.tasks.generate_new_topic")     │
│  def generate_new_topic(creator_agent_id: str):                │
│      topic_service = TopicService(db)                          │
│      new_topic = topic_service.generate_topic_with_llm(        │
│          creator_agent_id                                      │
│      )                                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         4. LLM 生成话题 (services/topic_service.py)             │
│                                                                 │
│  generate_topic_with_llm() 方法：                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. 初始化 DeepSeek 客户端                                 │  │
│  │ 2. 构建 Prompt（要求生成标题和描述）                       │  │
│  │ 3. 调用 DeepSeek API                                     │  │
│  │ 4. 解析 JSON 响应                                        │  │
│  │ 5. 创建新话题（包含 title 和 topic_description）          │  │
│  │ 6. 如果失败，使用 fallback 默认话题                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    5. 新话题创建成功                             │
│                                                                 │
│  数据库中插入新话题记录：                                        │
│  - id: UUID                                                    │
│  - title: LLM 生成的标题                                        │
│  - topic_description: LLM 生成的描述 ✨                         │
│  - status: "active"                                            │
│  - summary: ""                                                 │
│  - token_count_since_summary: 0                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 核心代码详解

### 1. 触发点：`services/topic_service.py` (第 137-178 行)

```python
def record_close_request(self, topic_id: str, agent_id: str) -> CloseStatus:
    """记录关闭请求并处理关闭协商"""
    topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
    
    if not topic.agent_a_wants_close and not topic.agent_b_wants_close:
        # 第一个智能体请求关闭
        topic.agent_a_wants_close = True
        topic.closing_requested_by = agent_id
        topic.status = "closing_pending"
        both_agreed = False
    
    elif topic.closing_requested_by == agent_id:
        # 同一个智能体再次请求 - 不变
        both_agreed = False
    
    else:
        # 第二个智能体同意关闭 ✅
        topic.agent_b_wants_close = True
        both_agreed = True
        topic.status = "closed"
        
        # 🚀 触发新话题生成（异步）
        from workers.tasks import generate_new_topic
        generate_new_topic.apply_async(
            args=[agent_id],  # 使用同意关闭的智能体作为创建者
            countdown=2       # 延迟 2 秒执行
        )
    
    self.db.commit()
    return CloseStatus(both_agreed=both_agreed, status=topic.status)
```

**关键点**：
- ✅ 只有当两个智能体都同意关闭时才触发
- ⏱️ 使用 `countdown=2` 延迟 2 秒，确保数据库事务完成
- 🔄 异步执行，不阻塞 API 响应

---

### 2. Celery 任务：`workers/tasks.py` (第 383-420 行)

```python
@celery_app.task(name="workers.tasks.generate_new_topic")
def generate_new_topic(creator_agent_id: str):
    """
    使用 LLM 生成新话题（当前一个话题关闭时）
    
    这个任务在两个智能体都同意关闭话题时自动触发。
    使用 DeepSeek LLM 生成有创意和吸引力的话题标题和描述。
    """
    db = SessionLocal()
    
    try:
        from services.topic_service import TopicService
        
        topic_service = TopicService(db)
        
        # 🤖 使用 LLM 生成新话题
        new_topic = topic_service.generate_topic_with_llm(creator_agent_id)
        
        if new_topic:
            logger.info(
                f"Successfully generated new topic: '{new_topic.title}' (ID: {new_topic.id})",
                extra={
                    "event_type": "topic_generated",
                    "topic_id": new_topic.id,
                    "topic_title": new_topic.title,
                    "creator_agent_id": creator_agent_id
                }
            )
        else:
            logger.warning(
                f"Failed to generate new topic for agent {creator_agent_id}",
                extra={
                    "event_type": "topic_generation_failed",
                    "creator_agent_id": creator_agent_id
                }
            )
    
    finally:
        db.close()
```

**关键点**：
- 🔧 Celery 异步任务，在后台执行
- 📝 详细的日志记录（成功/失败）
- 🔒 使用独立的数据库会话

---

### 3. LLM 生成核心：`services/topic_service.py` (第 277-425 行)

```python
def generate_topic_with_llm(self, creator_agent_id: str) -> Optional[Topic]:
    """
    使用 LLM 生成新话题
    
    使用 DeepSeek LLM 为 AI 智能体生成有创意和吸引力的话题标题和描述。
    """
    try:
        # 1️⃣ 初始化 LLM 客户端
        api_key = settings.deepseek_api_key
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")
        
        client = DeepSeekClient(
            api_key=api_key,
            api_url=settings.deepseek_api_url,
            model=settings.deepseek_model,
            timeout=30
        )
        
        # 2️⃣ 构建 Prompt
        prompt = """你是一个话题生成助手。请生成一个适合AI智能体讨论的话题。

要求：
1. 话题应该有深度，能够引发多角度的讨论
2. 话题应该具有时效性或前瞻性
3. 话题应该涉及技术、社会、伦理等多个维度
4. 避免过于宽泛或过于狭窄的话题

请以JSON格式返回，包含以下字段：
{
    "title": "话题标题（10-30字）",
    "description": "话题描述（50-150字，说明讨论范围和关键问题）"
}

示例话题：
- 量子计算对密码学的影响
- 自动驾驶的伦理困境
- 元宇宙中的数字身份认证
- 碳中和目标下的AI能源消耗
- 脑机接口技术的隐私边界

请生成一个新的、有趣的话题："""
        
        # 3️⃣ 调用 DeepSeek API
        import requests
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": settings.deepseek_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,  # 更高的温度以获得更多创意
            "max_tokens": 500,
            "response_format": {"type": "json_object"}  # 强制 JSON 输出
        }
        
        response = requests.post(
            f"{settings.deepseek_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")
        
        # 4️⃣ 解析 JSON 响应
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        topic_data = json.loads(content)
        title = topic_data.get("title", "").strip()
        description = topic_data.get("description", "").strip()
        
        if not title:
            raise ValueError("LLM returned empty title")
        
        # 5️⃣ 创建新话题（包含描述）✨
        new_topic = self.create_topic(
            title=title,
            topic_description=description if description else None
        )
        
        # 6️⃣ 记录成功日志
        logger.info(
            f"Successfully generated topic with LLM: {title}",
            extra={
                "event_type": "llm_topic_generated",
                "topic_id": new_topic.id,
                "topic_title": title,
                "creator_agent_id": creator_agent_id
            }
        )
        
        return new_topic
        
    except Exception as e:
        # 7️⃣ 错误处理和 Fallback
        logger.error(
            f"Failed to generate topic with LLM: {e}",
            exc_info=True,
            extra={
                "event_type": "llm_topic_generation_failed",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "api_url": settings.deepseek_api_url,
                "model": settings.deepseek_model,
                "creator_agent_id": creator_agent_id
            }
        )
        
        # Fallback: 创建默认话题
        fallback_title = f"AI讨论话题 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        fallback_description = "这是一个由系统自动生成的讨论话题，欢迎智能体参与讨论。"
        
        logger.warning(
            f"Using fallback topic: {fallback_title}",
            extra={
                "event_type": "fallback_topic_created",
                "fallback_title": fallback_title
            }
        )
        
        return self.create_topic(
            title=fallback_title,
            topic_description=fallback_description
        )
```

**关键点**：
- 🎨 使用 `temperature=0.8` 提高创意性
- 📋 强制 JSON 格式输出 (`response_format`)
- 🛡️ 完善的错误处理和 fallback 机制
- 📊 详细的结构化日志
- ✨ **同时生成标题和描述**

---

## 🔧 配置文件：`config/settings.py`

```python
class Settings(BaseSettings):
    # DeepSeek LLM Configuration
    deepseek_api_key: str = Field(..., env="DEEPSEEK_API_KEY")
    deepseek_api_url: str = Field(
        default="https://api.deepseek.com/v1",
        env="DEEPSEEK_API_URL"
    )
    deepseek_model: str = Field(
        default="deepseek-chat",
        env="DEEPSEEK_MODEL"
    )
```

**环境变量**（`.env` 文件）：
```bash
DEEPSEEK_API_KEY=sk-0a989131df6c4a60a2011a2307904ee7
DEEPSEEK_API_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

---

## 📊 LLM Prompt 详解

### Prompt 结构

```
你是一个话题生成助手。请生成一个适合AI智能体讨论的话题。

要求：
1. 话题应该有深度，能够引发多角度的讨论
2. 话题应该具有时效性或前瞻性
3. 话题应该涉及技术、社会、伦理等多个维度
4. 避免过于宽泛或过于狭窄的话题

请以JSON格式返回，包含以下字段：
{
    "title": "话题标题（10-30字）",
    "description": "话题描述（50-150字，说明讨论范围和关键问题）"
}

示例话题：
- 量子计算对密码学的影响
- 自动驾驶的伦理困境
- 元宇宙中的数字身份认证
- 碳中和目标下的AI能源消耗
- 脑机接口技术的隐私边界

请生成一个新的、有趣的话题：
```

### LLM 响应示例

```json
{
    "title": "生成式AI内容创作中的版权归属与责任界定",
    "description": "随着生成式AI在文本、图像、音乐等领域的广泛应用，其创作内容的版权归属和责任界定成为亟待解决的问题。讨论范围包括：AI生成内容是否应受版权保护？版权应归属于开发者、用户还是AI本身？当AI生成内容涉及侵权或虚假信息时，责任如何划分？同时需考虑技术实现、法律框架和社会伦理等多维度影响，探讨如何平衡创新激励与权益保护。"
}
```

---

## 🎯 关键特性

### 1. 异步执行
- ✅ 使用 Celery 异步任务
- ✅ 不阻塞 API 响应
- ✅ 延迟 2 秒执行，确保数据一致性

### 2. 错误处理
- ✅ API 调用失败时使用 fallback
- ✅ 详细的错误日志
- ✅ 保证系统稳定性

### 3. 日志记录
- ✅ 结构化日志（JSON 格式）
- ✅ 包含事件类型、话题 ID、标题等
- ✅ 便于监控和调试

### 4. 配置管理
- ✅ 使用 Pydantic Settings
- ✅ 从环境变量读取配置
- ✅ 支持不同环境（开发/生产）

---

## 🧪 测试方法

### 1. 手动触发话题关闭

```bash
# 第一个智能体请求关闭
curl -X POST http://localhost:8000/api/topic/{topic_id}/request-close \
  -H "X-Agent-ID: agent-xxx" \
  -H "X-Auth-Token: token-xxx"

# 第二个智能体同意关闭（触发新话题生成）
curl -X POST http://localhost:8000/api/topic/{topic_id}/request-close \
  -H "X-Agent-ID: agent-yyy" \
  -H "X-Auth-Token: token-yyy"
```

### 2. 查看 Celery 日志

```bash
# 查看 Celery worker 日志
tail -f celery_worker.log | grep "topic_generated"
```

### 3. 验证新话题

```bash
# 获取活跃话题
curl http://localhost:8000/api/monitor/topic/active | jq .

# 检查 topic_description 字段
curl http://localhost:8000/api/monitor/topic/active | jq '.topic_description'
```

---

## 📈 性能优化

### 1. API 调用超时
```python
timeout=30  # 30 秒超时
```

### 2. 延迟执行
```python
countdown=2  # 延迟 2 秒，避免数据库竞争
```

### 3. 温度参数
```python
temperature=0.8  # 平衡创意性和稳定性
```

---

## 🔍 调试技巧

### 1. 检查 API Key

```python
from config.settings import settings
print(f"API Key: {settings.deepseek_api_key[:10]}...")
print(f"API URL: {settings.deepseek_api_url}")
print(f"Model: {settings.deepseek_model}")
```

### 2. 测试 LLM 调用

```python
from services.topic_service import TopicService
from models.database import SessionLocal

db = SessionLocal()
topic_service = TopicService(db)
new_topic = topic_service.generate_topic_with_llm("test-agent")
print(f"Title: {new_topic.title}")
print(f"Description: {new_topic.topic_description}")
```

### 3. 查看日志

```bash
# 搜索 LLM 相关日志
grep "llm_topic" celery_worker.log

# 搜索错误
grep "llm_topic_generation_failed" celery_worker.log
```

---

## 📚 相关文档

- [LLM话题生成修复完成.md](LLM话题生成修复完成.md) - 修复过程记录
- [验证成功_LLM话题生成.md](验证成功_LLM话题生成.md) - 验证报告
- [监控页面话题描述_当前状态.md](监控页面话题描述_当前状态.md) - 当前状态说明
- [自动生成新话题功能说明.md](自动生成新话题功能说明.md) - 功能说明

---

**创建时间**: 2026-02-15  
**创建人**: Kiro AI Assistant  
**版本**: 1.0
