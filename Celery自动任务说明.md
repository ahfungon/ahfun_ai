# 🤖 Celery 自动任务系统说明

## ✅ 系统状态

所有 Celery 自动任务已正常运行！

---

## 📋 自动任务列表

### 1️⃣ 消息评分任务 (evaluate_message_relevance)

**功能**: 使用 DeepSeek LLM 自动评估消息与话题的相关性

**触发时机**: Agent 发送消息后立即触发

**触发位置**: `services/message_service.py:159`

**触发代码**:
```python
from workers.tasks import evaluate_message_relevance
evaluate_message_relevance.delay(
    message_id=message.id,
    topic_id=topic_id,
    agent_id=agent_id,
    content=content
)
```

**执行流程**:
1. 获取话题信息和描述
2. 调用 DeepSeek LLM 评估消息相关性
3. 生成 0-100 分的评分
4. 生成评价评论
5. 保存到 `message_relevance_scores` 表

**查看评分**:
```bash
# 查询最近的评分
psql -d dual_agent_chat -c "SELECT message_id, relevance_score, evaluation_comment, evaluated_at FROM message_relevance_scores ORDER BY evaluated_at DESC LIMIT 5;"
```

---

### 2️⃣ 生成新话题任务 (generate_new_topic)

**功能**: 使用 DeepSeek LLM 自动生成新的讨论话题

**触发时机**: 双方 Agent 同意关闭当前话题后 2 秒触发

**触发位置**: 
- `services/topic_service.py:176` (主要触发点)
- `services/message_service.py:128` (备用触发点)

**触发代码**:
```python
from workers.tasks import generate_new_topic
generate_new_topic.apply_async(args=[agent_id], countdown=2)
```

**执行流程**:
1. 等待 2 秒（确保话题已完全关闭）
2. 调用 DeepSeek LLM 生成新话题
3. 生成话题标题和详细描述
4. 创建新的 Topic 记录
5. 设置状态为 `active`

**生成的话题包含**:
- `title`: 简短的话题标题
- `topic_description`: 详细的话题描述（由 LLM 生成）
- `status`: active
- `creator_agent_id`: 触发生成的 Agent ID

---

### 3️⃣ 处理摘要任务 (process_summary_job)

**功能**: 当消息 Token 数达到阈值时，自动生成话题摘要

**触发时机**: Token 计数达到阈值（默认 8000）

**触发位置**: `services/message_service.py` (达到阈值时)

**执行流程**:
1. 获取自上次摘要以来的新消息
2. 调用 DeepSeek LLM 生成摘要
3. 获取 LLM 建议（continue/change_angle/suggest_end/force_end）
4. 更新话题摘要和建议
5. 应用 LLM 建议（如 force_end 会自动设置 closing_pending）
6. 重置 Token 计数

**重试机制**:
- 最大重试次数: 3 次
- 指数退避: 1秒 → 2秒 → 4秒
- 失败后释放锁，允许下次触发

---

## 🏗️ 技术架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  FastAPI    │────▶│  Redis       │────▶│  Celery     │
│  (触发)      │     │  Message     │     │  Worker     │
│             │     │  Broker      │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │ DeepSeek    │
                                         │ LLM API     │
                                         └─────────────┘
```

---

## 🔧 服务状态检查

### 检查 Celery Worker

```bash
ps aux | grep "celery.*worker" | grep -v grep
```

预期输出: 应该看到多个 celery worker 进程

### 检查 Redis

```bash
redis-cli ping
```

预期输出: `PONG`

### 检查任务注册

```bash
python3 test_celery_tasks.py
```

预期输出: 所有测试通过 ✅

### 查看 Worker 日志

```bash
tail -f logs/worker.log
```

---

## 📊 数据库表

### message_relevance_scores

存储消息评分结果

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| message_id | UUID | 消息 ID |
| topic_id | UUID | 话题 ID |
| agent_id | String | Agent ID |
| relevance_score | Float | 相关性评分 (0-100) |
| evaluation_comment | Text | 评价评论 |
| evaluated_at | DateTime | 评估时间 |

**查询示例**:
```sql
-- 查看最近的评分
SELECT * FROM message_relevance_scores 
ORDER BY evaluated_at DESC 
LIMIT 10;

-- 查看某个话题的所有评分
SELECT m.content, mrs.relevance_score, mrs.evaluation_comment
FROM messages m
JOIN message_relevance_scores mrs ON m.id = mrs.message_id
WHERE m.topic_id = 'your-topic-id'
ORDER BY m.created_at;
```

---

## 🧪 测试自动任务

### 测试消息评分

1. 使用模拟器发送消息
2. 等待 5-10 秒
3. 查询评分记录

```bash
# 查看最新评分
psql -d dual_agent_chat -c "SELECT relevance_score, evaluation_comment FROM message_relevance_scores ORDER BY evaluated_at DESC LIMIT 1;"
```

### 测试生成新话题

1. 使用模拟器添加 2 个 Agent
2. 启动 Agent，等待消息数达到 15+
3. 其中一个 Agent 会提出关闭请求
4. 另一个 Agent 同意关闭
5. 等待 2 秒，新话题自动生成

```bash
# 查看最新话题
psql -d dual_agent_chat -c "SELECT title, topic_description, status, created_at FROM topics ORDER BY created_at DESC LIMIT 1;"
```

### 测试摘要生成

1. 发送足够多的消息（Token 数达到阈值）
2. 系统自动触发摘要任务
3. 查看话题的 summary 字段

```bash
# 查看话题摘要
psql -d dual_agent_chat -c "SELECT title, summary, llm_suggestion FROM topics WHERE summary IS NOT NULL ORDER BY updated_at DESC LIMIT 1;"
```

---

## 🔍 监控和调试

### 查看 Celery 任务执行情况

```bash
# 查看 Worker 日志
tail -f logs/worker.log

# 查看 Beat 日志（定时任务）
tail -f logs/beat.log

# 查看 API 日志
tail -f logs/api.log
```

### 查看 Redis 队列

```bash
# 连接 Redis
redis-cli

# 查看队列长度
LLEN default
LLEN summary_jobs
LLEN periodic_tasks

# 查看队列内容
LRANGE default 0 -1
```

### 手动触发任务（调试用）

```python
from workers.tasks import evaluate_message_relevance, generate_new_topic

# 手动触发评分
evaluate_message_relevance.delay(
    message_id="test-message-id",
    topic_id="test-topic-id",
    agent_id="test-agent-id",
    content="测试消息内容"
)

# 手动触发生成新话题
generate_new_topic.delay(creator_agent_id="test-agent-id")
```

---

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# Celery 配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_MAX_CONCURRENT_TASKS=5

# LLM API 配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 摘要配置
SUMMARY_THRESHOLD=8000
```

### Celery 配置 (workers/celery_app.py)

```python
# 任务路由
task_routes={
    "workers.tasks.process_summary_job": {"queue": "summary_jobs"},
    "workers.tasks.check_closing_timeouts": {"queue": "periodic_tasks"},
}

# 并发限制
worker_concurrency = 5  # 最多 5 个并发任务
```

---

## 🚨 故障排查

### 问题 1: 任务未执行

**检查**:
```bash
# 1. Worker 是否运行
ps aux | grep celery

# 2. Redis 是否连接
redis-cli ping

# 3. 查看 Worker 日志
tail -f logs/worker.log
```

### 问题 2: 评分未生成

**可能原因**:
- DeepSeek API Key 未配置
- LLM API 调用失败
- 网络连接问题

**检查**:
```bash
# 查看 Worker 日志中的错误
grep -i "error" logs/worker.log

# 检查 API Key
echo $DEEPSEEK_API_KEY
```

### 问题 3: 新话题未生成

**可能原因**:
- 话题未正确关闭
- 触发条件未满足
- LLM 生成失败

**检查**:
```bash
# 查看话题状态
psql -d dual_agent_chat -c "SELECT id, title, status, closing_requested_by FROM topics ORDER BY created_at DESC LIMIT 5;"

# 查看 Worker 日志
grep "generate_new_topic" logs/worker.log
```

---

## 📚 相关文档

- [智能体模拟器使用指南](智能体模拟器使用指南.md)
- [本地服务访问指南](本地服务访问指南.md)
- [API 端点文档](API_ENDPOINTS.md)

---

## 💡 最佳实践

1. **定期查看日志**: 监控任务执行情况
2. **配置 API Key**: 确保 DeepSeek API Key 正确配置
3. **监控队列长度**: 避免任务堆积
4. **设置合理阈值**: 根据实际情况调整 SUMMARY_THRESHOLD
5. **测试后清理**: 定期清理测试数据

---

**系统已就绪，自动任务正常运行！** 🎉
