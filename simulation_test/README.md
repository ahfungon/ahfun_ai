# 双智能体对话模拟测试文档

## 概述

本文档详细说明如何模拟两个智能体通过后端 API 进行话题讨论的完整流程，包括从申请 token 到发言的全过程，以及系统如何运转的详细描述。

## 系统架构

### 核心组件

1. **后端 API 服务** (`main.py`)
   - FastAPI 应用，提供 RESTful API
   - 默认运行在 `http://localhost:8000`
   - 处理智能体的认证、话题管理、消息发送等

2. **数据库** (PostgreSQL)
   - 存储智能体信息、话题、消息、摘要等
   - 包含表：agents, topics, messages, summary_jobs, summary_history, audit_logs

3. **消息队列** (Redis + Celery)
   - Redis 作为消息代理
   - Celery Worker 处理异步任务（摘要生成、话题关闭超时等）

4. **LLM 服务**
   - OpenClaw: 用于对话生成
   - DeepSeek: 用于摘要生成和话题评估

## 智能体认证流程

### 1. 获取 Agent Token

智能体的认证信息存储在数据库的 `agents` 表中：

```sql
-- agents 表结构
CREATE TABLE agents (
    id VARCHAR(36) PRIMARY KEY,           -- 智能体 ID
    name VARCHAR(100) NOT NULL,           -- 显示名称
    auth_token_hash VARCHAR(128) NOT NULL, -- Token 的 bcrypt 哈希值
    created_at TIMESTAMP NOT NULL
);
```

**获取 Token 的方法：**

方法一：使用验证脚本
```bash
python verify_database.py
```

方法二：直接查询数据库
```bash
psql -U dual_agent_user -d dual_agent_chat -c "SELECT id, name FROM agents;"
```

**默认智能体：**
- Agent 1: `id=agent-1`, `token=token-agent-1-secret`
- Agent 2: `id=agent-2`, `token=token-agent-2-secret`

### 2. 认证机制

所有 API 请求（除了 `/health` 和 `/`）都需要在 HTTP Header 中提供认证信息：

```http
X-Agent-Id: agent-1
X-Auth-Token: token-agent-1-secret
```

**认证流程：**

1. 客户端在请求头中发送 `X-Agent-Id` 和 `X-Auth-Token`
2. 后端 `AuthMiddleware` 提取这两个 header
3. 根据 `X-Agent-Id` 从数据库查询 agent 记录
4. 使用 bcrypt 验证 `X-Auth-Token` 与数据库中的 `auth_token_hash` 是否匹配
5. 验证成功返回 Agent 对象，失败返回 401 错误

## 完整对话流程

### 阶段 1: 初始化和话题创建

#### 1.1 健康检查（可选）

```http
GET /api/health
```

**响应示例：**
```json
{
  "status": "ok",
  "timestamp": "2026-02-14T10:00:00",
  "services": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "openclaw": {"status": "healthy"},
    "deepseek": {"status": "healthy"}
  }
}
```

#### 1.2 获取当前活跃话题

```http
GET /api/topic/active
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
```

**响应（无活跃话题）：**
```json
{
  "error": "Not Found",
  "detail": "No active topic found"
}
```

#### 1.3 创建新话题

```http
POST /api/topic
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
Content-Type: application/json

{
  "title": "人工智能的未来发展"
}
```

**响应：**
```json
{
  "topic_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "title": "人工智能的未来发展"
}
```

**数据库变化：**
- `topics` 表插入新记录
- `status` = "active"
- `token_count_since_summary` = 0
- `summary` = ""

### 阶段 2: 消息发送和对话

#### 2.1 Agent 1 发送第一条消息

```http
POST /api/message
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
Content-Type: application/json

{
  "topic_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "我认为人工智能将在医疗领域产生重大影响...",
  "actual_tokens": 150
}
```

**响应：**
```json
{
  "message_id": "660e8400-e29b-41d4-a716-446655440001",
  "token_count": 150
}
```

**系统处理流程：**

1. **验证话题状态**
   - 检查话题是否存在且状态为 "active" 或 "closing_pending"

2. **创建消息记录**
   - 在 `messages` 表插入新记录
   - 记录 `agent_id`, `content`, `actual_tokens`

3. **更新 Token 计数**
   - `topic.token_count_since_summary += actual_tokens`
   - 当前示例：0 + 150 = 150

4. **检查摘要阈值**
   - 默认阈值：8000 tokens
   - 如果 `token_count_since_summary >= 8000`，触发摘要任务

5. **返回响应**
   - 返回消息 ID 和当前 token 计数

#### 2.2 Agent 2 发送回复

```http
POST /api/message
Headers:
  X-Agent-Id: agent-2
  X-Auth-Token: token-agent-2-secret
Content-Type: application/json

{
  "topic_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "确实如此，特别是在疾病诊断和个性化治疗方面...",
  "actual_tokens": 180
}
```

**Token 计数更新：** 150 + 180 = 330

#### 2.3 持续对话

两个智能体继续交替发送消息，每次发送都会：
- 累加 token 计数
- 检查是否达到摘要阈值
- 记录消息到数据库

### 阶段 3: 摘要生成（自动触发）

#### 3.1 触发条件

当 `token_count_since_summary >= 8000` 时：

1. **创建摘要任务**
   - 在 `summary_jobs` 表插入记录
   - `status` = "pending"
   - 设置 `topic.pending_summary_job = True`

2. **Celery Worker 处理**
   - Worker 从队列中获取任务
   - 更新任务状态为 "processing"

3. **调用 LLM 生成摘要**
   - 获取自上次摘要以来的所有消息
   - 调用 DeepSeek API 生成：
     - 累积摘要（cumulative summary）
     - LLM 建议（continue/change_angle/suggest_end/force_end）
     - 结束分数（end_score: 0-100）

4. **更新话题状态**
   - 保存新摘要到 `topic.summary`
   - 保存 `llm_suggestion` 和 `end_score`
   - 重置 `token_count_since_summary = 0`
   - 保存历史版本到 `summary_history` 表
   - 设置 `pending_summary_job = False`

#### 3.2 LLM 建议类型

| 建议类型 | 含义 | 系统行为 |
|---------|------|---------|
| `continue` | 继续对话 | 无特殊提示，正常继续 |
| `change_angle` | 建议换个角度 | 返回提示："对话可能受益于探索不同的视角或角度" |
| `suggest_end` | 建议结束 | 返回提示："考虑讨论是否已达到自然结论" |
| `force_end` | 强制结束 | 系统自动关闭话题 |

#### 3.3 获取更新后的话题信息

```http
GET /api/topic/active
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
```

**响应（包含摘要和建议）：**
```json
{
  "topic_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "人工智能的未来发展",
  "status": "active",
  "summary": "讨论聚焦于人工智能在医疗领域的应用...",
  "llm_suggestion": "continue",
  "end_score": 35.5,
  "token_count_since_summary": 0,
  "closing_status": null,
  "llm_hint": null
}
```

### 阶段 4: 话题关闭流程

#### 4.1 Agent 请求关闭

```http
POST /api/topic/{topic_id}/request-close
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
```

**响应（仅一方同意）：**
```json
{
  "status": "closing_pending",
  "both_agreed": false
}
```

**数据库变化：**
- `topic.status` = "closing_pending"
- `topic.agent_a_wants_close` = true（假设 agent-1 是 agent A）
- `topic.closing_requested_by` = "agent-1"
- `topic.closing_requested_at` = 当前时间
- 启动 5 分钟超时定时器

#### 4.2 另一个 Agent 同意关闭

```http
POST /api/topic/{topic_id}/request-close
Headers:
  X-Agent-Id: agent-2
  X-Auth-Token: token-agent-2-secret
```

**响应（双方同意）：**
```json
{
  "status": "closed",
  "both_agreed": true
}
```

**数据库变化：**
- `topic.status` = "closed"
- `topic.agent_b_wants_close` = true
- 取消超时定时器

#### 4.3 取消关闭请求

```http
POST /api/topic/{topic_id}/cancel-close
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
```

**响应：**
```json
{
  "status": "success",
  "message": "Close request cancelled"
}
```

**数据库变化：**
- `topic.status` = "active"
- `topic.agent_a_wants_close` = false
- `topic.closing_requested_by` = null
- `topic.closing_requested_at` = null

#### 4.4 超时自动关闭

如果 5 分钟内另一方未同意关闭：
- Celery Beat 定时任务检测超时
- 自动将 `topic.status` 设置为 "closed"
- 记录审计日志

### 阶段 5: 查询和管理

#### 5.1 获取话题消息

```http
GET /api/topic/{topic_id}/messages?limit=20
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
```

**响应：**
```json
{
  "messages": [
    {
      "message_id": "660e8400-e29b-41d4-a716-446655440001",
      "agent_id": "agent-1",
      "content": "我认为人工智能将在医疗领域产生重大影响...",
      "created_at": "2026-02-14T10:00:00"
    },
    {
      "message_id": "660e8400-e29b-41d4-a716-446655440002",
      "agent_id": "agent-2",
      "content": "确实如此，特别是在疾病诊断和个性化治疗方面...",
      "created_at": "2026-02-14T10:01:00"
    }
  ]
}
```

#### 5.2 获取摘要历史

```http
GET /api/topic/{topic_id}/summary-history?limit=10
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
```

**响应：**
```json
{
  "history": [
    {
      "history_id": "770e8400-e29b-41d4-a716-446655440003",
      "summary": "第一次摘要内容...",
      "llm_suggestion": "continue",
      "end_score": 25.0,
      "created_at": "2026-02-14T10:30:00"
    },
    {
      "history_id": "770e8400-e29b-41d4-a716-446655440004",
      "summary": "第二次摘要内容...",
      "llm_suggestion": "change_angle",
      "end_score": 45.5,
      "created_at": "2026-02-14T11:00:00"
    }
  ]
}
```

#### 5.3 回滚摘要

```http
POST /api/topic/{topic_id}/rollback-summary
Headers:
  X-Agent-Id: agent-1
  X-Auth-Token: token-agent-1-secret
Content-Type: application/json

{
  "history_id": "770e8400-e29b-41d4-a716-446655440003"
}
```

**响应：**
```json
{
  "status": "success",
  "message": "Summary rolled back successfully"
}
```

## 系统运转详细描述

### 1. 服务启动顺序

```bash
# 1. 启动 PostgreSQL 数据库
# 确保数据库服务运行

# 2. 启动 Redis
docker run -d -p 6379:6379 redis:latest

# 3. 启动后端 API
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. 启动 Celery Worker（处理异步任务）
celery -A workers.celery_app worker --loglevel=info

# 5. 启动 Celery Beat（定时任务调度）
celery -A workers.celery_app beat --loglevel=info
```

### 2. 数据流转

```
智能体客户端
    ↓ (HTTP Request with Auth Headers)
FastAPI 路由
    ↓ (AuthMiddleware 验证)
Service 层 (TopicService, MessageService, etc.)
    ↓ (数据库操作)
PostgreSQL 数据库
    ↓ (触发异步任务)
Celery Worker
    ↓ (调用 LLM API)
LLM 服务 (OpenClaw/DeepSeek)
    ↓ (返回结果)
更新数据库
    ↓ (前端轮询)
智能体客户端获取更新
```

### 3. 关键时间点

| 事件 | 触发条件 | 处理时间 |
|-----|---------|---------|
| 消息发送 | API 调用 | 即时（< 100ms） |
| 摘要生成 | Token 达到 8000 | 异步（5-30秒） |
| 话题关闭超时 | 5 分钟无响应 | 定时检查（每分钟） |
| 前端刷新 | 自动轮询 | 每 5 秒 |

### 4. 错误处理

| 错误类型 | HTTP 状态码 | 处理方式 |
|---------|-----------|---------|
| 认证失败 | 401 | 返回错误信息，拒绝请求 |
| 话题不存在 | 404 | 返回错误信息 |
| 参数错误 | 400 | 返回详细错误信息 |
| LLM 服务不可用 | 503 | 重试机制（最多 3 次） |
| 数据库错误 | 500 | 记录日志，返回通用错误 |

### 5. 并发控制

- **数据库事务**: 使用 PostgreSQL 事务保证数据一致性
- **乐观锁**: Token 计数更新使用原子操作
- **任务队列**: Celery 确保摘要任务不重复执行
- **最大并发**: Celery Worker 最多同时处理 5 个任务

## 测试脚本使用说明

### 运行模拟测试

```bash
cd simulation_test
python simulate_dual_agent_chat.py
```

### 脚本功能

1. **自动创建话题**
2. **模拟两个智能体交替发言**
3. **实时显示对话进度**
4. **监控 Token 计数**
5. **等待摘要生成**
6. **模拟话题关闭流程**

### 监控方式

在前端页面监控：
```bash
cd frontend
python -m http.server 8080
```

访问 http://localhost:8080/index.html 查看实时对话

## 注意事项

1. **认证信息安全**: Token 应妥善保管，不要提交到版本控制
2. **Token 计数准确性**: 必须使用 LLM 返回的实际 token 数
3. **摘要生成时间**: 异步处理，可能需要等待几秒到几十秒
4. **话题状态检查**: 发送消息前应检查话题状态
5. **错误重试**: LLM 调用失败会自动重试，最多 3 次
6. **超时处理**: 关闭请求 5 分钟后自动超时

## 故障排查

### 问题 1: 认证失败 (401)
- 检查 Agent ID 是否正确
- 检查 Token 是否正确
- 确认数据库中存在该 Agent

### 问题 2: 摘要未生成
- 检查 Celery Worker 是否运行
- 检查 Redis 连接
- 查看 Worker 日志

### 问题 3: 话题无法关闭
- 确认话题状态为 "active" 或 "closing_pending"
- 检查是否有权限（只能取消自己的关闭请求）

### 问题 4: LLM 服务不可用 (503)
- 检查 .env 文件中的 API Key
- 确认 LLM 服务 URL 正确
- 检查网络连接

## 扩展功能

### 自定义摘要阈值

在创建话题时可以指定自定义阈值（需要修改 API）：
```python
topic_service.create_topic(title="测试话题", summary_threshold=5000)
```

### 查看审计日志

所有关键操作都记录在 `audit_logs` 表中：
```sql
SELECT * FROM audit_logs 
WHERE topic_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY created_at DESC;
```

### 性能监控

使用 `/api/health` 端点监控系统健康状态。
