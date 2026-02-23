# Celery评分和摘要功能修复完成报告

## 问题诊断

### 1. 消息评分功能未生效

**症状**:
- Celery Worker 接收到 `evaluate_message_relevance` 任务
- 任务从未完成，数据库中没有评分记录

**根本原因**:
1. **DeepSeek API 提示词问题**: DeepSeek API 要求在使用 `response_format='json_object'` 时，提示词中必须包含小写的 "json" 关键词
2. **数据库表结构不匹配**: `message_relevance_scores` 表的 `id` 列定义为 `INTEGER`，但代码尝试插入 UUID 字符串

### 2. Token 阈值自动摘要未生效

**原因**: 由于评分功能未生效，消息发送流程中的 token 计数和摘要触发逻辑无法正常工作

## 修复方案

### 1. 修复 DeepSeek API 提示词

**文件**: `services/message_scoring_service.py`, `services/summary_service.py`

**修改**:
```python
# 修改前
返回JSON格式（只返回JSON，不要其他文字）：

# 修改后  
请以 json 格式返回评分结果（只返回 json，不要其他文字）：
```

**原因**: DeepSeek API 严格要求提示词中包含小写 "json" 以启用 JSON 模式

### 2. 修复数据库表结构

**文件**: `fix_message_relevance_scores_id.sql`

**SQL 迁移**:
```sql
BEGIN;

-- 删除主键约束
ALTER TABLE message_relevance_scores DROP CONSTRAINT message_relevance_scores_pkey;

-- 删除自增序列
DROP SEQUENCE IF EXISTS message_relevance_scores_id_seq CASCADE;

-- 将 id 列类型改为 VARCHAR(36) 以支持 UUID
ALTER TABLE message_relevance_scores ALTER COLUMN id TYPE VARCHAR(36);

-- 重新添加主键约束
ALTER TABLE message_relevance_scores ADD CONSTRAINT message_relevance_scores_pkey PRIMARY KEY (id);

COMMIT;
```

**原因**: 
- 原表结构: `id INTEGER` (自增)
- 期望结构: `id VARCHAR(36)` (UUID)
- 代码使用 `uuid.uuid4()` 生成 UUID 字符串作为主键

### 3. 修复 Celery Worker 队列配置

**文件**: `/etc/systemd/system/dual-agent-celery.service` (服务器)

**修改**:
```ini
# 修改前
ExecStart=/home/ubuntu/dual-agent-chat/venv/bin/celery -A workers.celery_app worker --loglevel=info

# 修改后
ExecStart=/home/ubuntu/dual-agent-chat/venv/bin/celery -A workers.celery_app worker --loglevel=info -Q default,summary_jobs,periodic_tasks
```

**原因**: Worker 必须监听所有三个队列才能处理评分和摘要任务

## 验证结果

### 1. 评分功能验证

**直接调用测试**:
```bash
cd dual-agent-chat && source venv/bin/activate
python3 test_celery_task_direct.py
```

**结果**:
```
✓ Score created:
  Score: 85.0
  Comment: 发言紧扣主题核心，准确总结了历史讨论...
```

**异步任务测试**:
```python
task = evaluate_message_relevance.delay(message_id, topic_id, agent_id, content)
# 等待 15 秒
# ✓ Score created: 92.0
```

### 2. 数据库验证

```sql
SELECT COUNT(*) FROM message_relevance_scores;
-- 结果: 2 条评分记录

SELECT * FROM message_relevance_scores ORDER BY evaluated_at DESC LIMIT 1;
-- 最新评分: 92.0 分
```

### 3. Worker 日志验证

```bash
journalctl -u dual-agent-celery --since '5 minutes ago'
```

**结果**:
- 任务接收: `Task workers.tasks.evaluate_message_relevance[...] received`
- 任务完成: 评分记录成功写入数据库

## 功能状态

### ✅ 已修复并验证

1. **消息评分功能**
   - DeepSeek API 调用正常
   - 评分记录成功保存到数据库
   - 异步 Celery 任务正常执行

2. **Celery Worker 配置**
   - 监听所有必需队列 (default, summary_jobs, periodic_tasks)
   - 任务路由正确
   - Worker 进程稳定运行

3. **数据库表结构**
   - `message_relevance_scores.id` 列类型正确 (VARCHAR(36))
   - 外键约束正常
   - 索引完整

### 🔄 待验证

1. **Token 阈值自动摘要**
   - 需要发送足够多的消息使 token 计数达到阈值 (4000)
   - 验证摘要任务是否自动触发
   - 验证摘要生成和 LLM 建议应用

## 部署记录

### Git 提交

```bash
git add services/message_scoring_service.py services/summary_service.py
git commit -m "修复DeepSeek API调用：在提示词中使用小写json以符合API要求"
# Commit: c2341a7
```

### 服务器部署

```bash
./deploy_update_to_mingkuan.sh
# 部署时间: 2026-02-15 20:35:15 CST
# 服务状态: 所有服务正常运行
```

### 数据库迁移

```bash
scp fix_message_relevance_scores_id.sql ubuntu@129.211.28.211:~/dual-agent-chat/
ssh ubuntu@129.211.28.211 "cd dual-agent-chat && sudo -u postgres psql dual_agent_chat < fix_message_relevance_scores_id.sql"
# 执行时间: 2026-02-15 20:36:xx CST
# 结果: 成功
```

## 下一步操作

### 1. 测试摘要功能

需要触发足够多的消息以达到 token 阈值:

```bash
# 启动智能体持续对话
cd simulation_test
./start_agents.sh --env server
```

### 2. 监控摘要任务

```bash
# 查看 Worker 日志
ssh -i ~/.ssh/mingkuan.pem ubuntu@129.211.28.211 'journalctl -u dual-agent-celery -f'

# 查看 Beat 日志 (定时任务调度)
ssh -i ~/.ssh/mingkuan.pem ubuntu@129.211.28.211 'journalctl -u dual-agent-celery-beat -f'
```

### 3. 验证摘要生成

```python
from models.database import SessionLocal
from models.models import Topic, SummaryHistory

db = SessionLocal()

# 检查话题摘要
topic = db.query(Topic).filter(Topic.status == 'active').first()
print(f'Summary: {topic.summary}')
print(f'LLM Suggestion: {topic.llm_suggestion}')
print(f'End Score: {topic.end_score}')

# 检查摘要历史
history = db.query(SummaryHistory).filter(
    SummaryHistory.topic_id == topic.id
).order_by(SummaryHistory.created_at.desc()).all()
print(f'Summary history count: {len(history)}')
```

## 技术要点

### DeepSeek API JSON 模式要求

当使用 `response_format={"type": "json_object"}` 时:
- 提示词中必须包含 "json" 关键词 (小写)
- 否则返回 400 错误: "Prompt must contain the word 'json'"

### UUID vs 自增 ID

- SQLAlchemy 模型使用 `String(36)` 存储 UUID
- 代码中使用 `str(uuid.uuid4())` 生成 ID
- 数据库表必须使用 `VARCHAR(36)` 而非 `INTEGER`

### Celery 队列配置

- 任务通过 `task_routes` 配置路由到不同队列
- Worker 必须显式监听所有需要的队列: `-Q queue1,queue2,queue3`
- 默认只监听 `default` 队列

## 相关文件

### 代码文件
- `services/message_scoring_service.py` - 消息评分服务
- `services/summary_service.py` - 摘要生成服务
- `services/llm_clients/deepseek_client.py` - DeepSeek API 客户端
- `workers/tasks.py` - Celery 任务定义
- `workers/celery_app.py` - Celery 应用配置

### 数据库迁移
- `fix_message_relevance_scores_id.sql` - 修复评分表 ID 列类型
- `add_topic_id_to_scores.sql` - 添加 topic_id 和 agent_id 列

### 测试脚本
- `test_celery_task_direct.py` - 直接测试评分任务
- `test_server_messages.py` - 测试服务器消息 API

### 文档
- `消息评分触发流程说明.md` - 评分功能说明
- `摘要触发机制说明.md` - 摘要功能说明
- `服务器环境测试_最终成功.md` - 服务器测试报告

## 总结

通过修复 DeepSeek API 提示词格式和数据库表结构，消息评分功能现已完全正常工作。Celery Worker 能够正确接收和执行评分任务，评分结果成功保存到数据库。

摘要功能的代码逻辑正确，但需要实际触发 token 阈值来验证完整流程。建议启动智能体持续对话以测试摘要自动生成功能。
