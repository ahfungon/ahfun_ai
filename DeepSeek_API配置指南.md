# DeepSeek API 配置指南

## 概述

系统中有三个核心功能依赖 DeepSeek API：

1. **消息评分功能** - 自动评估每条消息的相关性（0-100分）
2. **对话总结功能** - 定期生成对话总结和建议
3. **自动生成新话题** - 话题关闭后自动生成新话题

当前这些功能都无法正常工作，因为 DeepSeek API Key 未配置。

## 快速配置（3步）

### 1. 获取 API Key

访问 [DeepSeek 平台](https://platform.deepseek.com/)：
- 注册/登录账号
- 进入 "API Keys" 页面
- 点击 "Create API Key"
- 复制生成的 Key（格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxx`）

### 2. 配置到 .env 文件

编辑项目根目录的 `.env` 文件：

```bash
# 将这一行：
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 替换为：
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx  # 你的真实 API Key
```

### 3. 重启服务

```bash
# 停止所有 Celery 进程
pkill -f 'celery.*worker'
pkill -f 'celery.*beat'

# 重新启动（推荐使用 quick_start.py）
python quick_start.py
```

## 验证配置

运行诊断脚本：

```bash
python test_scoring_issue.py
```

成功的输出应该显示：
```
✅ DeepSeek API Key 已配置
✅ API Key 有效
```

## 受影响的功能详解

### 1. 消息评分功能

**功能说明：**
- 每条消息发送后，自动调用 DeepSeek LLM 评估相关性
- 评分维度：主题相关性（40%）+ 内容质量（30%）+ 讨论推进（30%）
- 评分范围：0-100 分

**触发时机：**
- 用户或智能体发送消息时自动触发
- 异步执行，不阻塞消息发送

**数据存储：**
- 表：`message_relevance_scores`
- 字段：`relevance_score`（分数）、`evaluation_comment`（评价）

**代码位置：**
- `services/message_service.py` - 触发评分任务
- `services/message_scoring_service.py` - 评分服务实现
- `workers/tasks.py` - `evaluate_message_relevance()` 任务

**验证方法：**
```bash
# 发送一条消息后，查询评分记录
python -c "
from models.database import SessionLocal
from models.models import MessageRelevanceScore

db = SessionLocal()
scores = db.query(MessageRelevanceScore).order_by(MessageRelevanceScore.evaluated_at.desc()).limit(5).all()

print('最近的评分记录：')
for score in scores:
    print(f'  消息ID: {score.message_id}')
    print(f'  评分: {score.relevance_score}')
    print(f'  评论: {score.evaluation_comment}')
    print()

db.close()
"
```

---

### 2. 对话总结功能

**功能说明：**
- 当对话超过 8000 tokens 时，自动生成总结
- LLM 会分析对话内容，给出建议（continue/change_angle/suggest_end/force_end）
- 提供结束评分（end_score: 0-100）

**触发时机：**
- 消息发送后，token 计数超过阈值（默认 8000）
- 自动创建 `SummaryJob` 并由 Celery Worker 处理

**数据存储：**
- 表：`summary_history` - 历史总结记录
- 表：`topics` - 更新 `summary`、`llm_suggestion`、`end_score` 字段

**代码位置：**
- `services/summary_service.py` - 总结服务实现
- `workers/tasks.py` - `process_summary_job()` 任务

**验证方法：**
```bash
# 查看最近的总结记录
python -c "
from models.database import SessionLocal
from models.models import SummaryHistory

db = SessionLocal()
summaries = db.query(SummaryHistory).order_by(SummaryHistory.created_at.desc()).limit(3).all()

print('最近的总结记录：')
for summary in summaries:
    print(f'  话题ID: {summary.topic_id}')
    print(f'  建议: {summary.suggestion}')
    print(f'  结束评分: {summary.end_score}')
    print(f'  总结: {summary.summary[:100]}...')
    print()

db.close()
"
```

---

### 3. 自动生成新话题

**功能说明：**
- 当话题被关闭时（双方智能体同意结束），自动生成新话题
- LLM 会创造有趣、有深度的话题标题和描述

**触发时机：**
- 双方智能体都请求关闭话题时
- 自动调用 `generate_new_topic.delay()` Celery 任务

**数据存储：**
- 表：`topics` - 创建新的话题记录
- 状态：`active`（新话题自动激活）

**代码位置：**
- `services/topic_service.py` - `generate_topic_with_llm()` 方法
- `workers/tasks.py` - `generate_new_topic()` 任务

**验证方法：**
```bash
# 查看最近创建的话题
python -c "
from models.database import SessionLocal
from models.models import Topic

db = SessionLocal()
topics = db.query(Topic).order_by(Topic.created_at.desc()).limit(5).all()

print('最近的话题：')
for topic in topics:
    print(f'  标题: {topic.title}')
    print(f'  状态: {topic.status}')
    print(f'  创建时间: {topic.created_at}')
    print()

db.close()
"
```

---

## 配置参数说明

在 `.env` 文件中，DeepSeek 相关的配置参数：

```bash
# DeepSeek API Key（必需）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# DeepSeek API URL（可选，默认值如下）
DEEPSEEK_API_URL=https://api.deepseek.com/v1

# DeepSeek 模型（可选，默认值如下）
DEEPSEEK_MODEL=deepseek-chat
```

## 成本估算

DeepSeek API 的定价（截至 2024 年）：

- **输入 tokens**: ¥0.001 / 1K tokens
- **输出 tokens**: ¥0.002 / 1K tokens

**每日成本估算（假设 100 条消息）：**

| 功能 | 每次调用 tokens | 每日调用次数 | 每日成本 |
|------|----------------|-------------|---------|
| 消息评分 | ~500 tokens | 100 次 | ¥0.10 |
| 对话总结 | ~2000 tokens | 2 次 | ¥0.01 |
| 生成新话题 | ~1000 tokens | 1 次 | ¥0.003 |
| **总计** | - | - | **¥0.11/天** |

**月成本约 ¥3.3**（非常经济）

## 故障排查

### 问题 1：配置了 API Key 但功能仍不工作

**解决方案：**
1. 确认已重启 Celery Worker
2. 检查 API Key 格式是否正确（应以 `sk-` 开头）
3. 运行诊断脚本：`python test_scoring_issue.py`

### 问题 2：API 调用失败

**可能原因：**
- 网络问题（无法访问 DeepSeek API）
- API Key 无效或过期
- API 配额用尽
- API URL 配置错误

**排查步骤：**
```bash
# 测试网络连接
curl -I https://api.deepseek.com/v1

# 测试 API Key
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 问题 3：Celery Worker 未运行

**检查方法：**
```bash
ps aux | grep celery | grep -v grep
```

**启动方法：**
```bash
python quick_start.py
```

## 相关文件

- `.env` - 环境变量配置
- `config/settings.py` - 配置加载
- `services/llm_clients/deepseek_client.py` - DeepSeek API 客户端
- `services/message_scoring_service.py` - 消息评分服务
- `services/summary_service.py` - 总结服务
- `services/topic_service.py` - 话题服务
- `workers/tasks.py` - Celery 异步任务
- `test_scoring_issue.py` - 诊断脚本

## 下一步

配置完成后，建议：

1. **测试消息评分**：发送几条消息，查看评分记录
2. **测试对话总结**：发送足够多的消息（超过 8000 tokens），触发总结
3. **测试生成新话题**：关闭一个话题，观察是否自动生成新话题
4. **监控 Celery 日志**：确保任务正常执行

## 技术支持

如遇问题，请查看：
- `消息评分功能故障排查报告.md` - 详细的评分功能排查指南
- Celery Worker 日志 - 查看任务执行情况
- 数据库记录 - 验证数据是否正确保存
