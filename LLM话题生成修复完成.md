# LLM 话题生成功能修复完成

## 问题诊断

### 现象
- 最近生成的话题都是备用方案（"AI讨论话题 2026-02-15..."）
- LLM 调用失败，导致使用 fallback 逻辑

### 根本原因
`services/topic_service.py` 中的 `generate_topic_with_llm()` 方法使用了错误的方式获取 API Key：

```python
# 错误的方式
api_key = os.getenv("DEEPSEEK_API_KEY", "")
```

这种方式在某些情况下无法正确加载环境变量，导致 API Key 为空。

## 解决方案

### 修复代码
修改 `services/topic_service.py` 第 295 行，使用 Pydantic Settings 配置：

```python
# 正确的方式
api_key = settings.deepseek_api_key
```

### 配置验证
确认配置文件已正确设置：

1. **config/settings.py** - 已添加 `deepseek_model` 字段：
```python
deepseek_model: str = Field(
    default="deepseek-chat",
    description="DeepSeek model name"
)
```

2. **.env** - API Key 已配置：
```
DEEPSEEK_API_KEY=sk-0a989131df6c4a60a2011a2307904ee7
DEEPSEEK_API_URL=https://api.deepseek.com/v1
```

## 测试验证

### 测试结果
```bash
python3 -c "from models.database import SessionLocal; from services.topic_service import TopicService; db = SessionLocal(); topic = TopicService(db).generate_topic_with_llm('test'); print(f'标题: {topic.title}'); db.close()"
```

**输出：**
```
✓ 成功生成话题!
ID: 96d0d2a9-5841-419c-931f-7c43f8c95d59
标题: 生成式AI内容创作中的版权归属与责任界定
描述: 随着生成式AI在文本、图像、音乐等领域的广泛应用，其创作内容的版权归属和责任界定成为亟待解决的问题...
状态: active
✓ 这是 LLM 生成的话题
```

## 部署步骤

### 1. 重启 Celery Worker
```bash
# 停止旧的 worker
pkill -f "celery.*worker"

# 启动新的 worker（加载最新代码）
celery -A workers.celery_app worker --loglevel=info -Q default,summary_jobs,periodic_tasks
```

### 2. 验证服务状态
```bash
# 检查 Celery worker
ps aux | grep "celery.*worker"

# 检查智能体
ps aux | grep "autonomous_agent.py"
```

## Git 提交

```bash
git add services/topic_service.py config/settings.py
git commit -m "修复LLM话题生成：使用settings.deepseek_api_key替代os.getenv()"
```

**Commit Hash:** a42c50b

## 下一步验证

### 等待下次话题关闭
当前智能体正在运行，等待下次话题关闭时，系统会自动触发 `generate_new_topic` Celery 任务。

### 预期行为
1. 双方智能体协商关闭话题（2 轮对话后，4 条消息）
2. 第二个同意的智能体触发 `generate_new_topic` 任务
3. Celery worker 调用 `TopicService.generate_topic_with_llm()`
4. DeepSeek LLM 生成创意话题标题和描述
5. 新话题自动创建，状态为 `active`
6. 智能体自动切换到新话题继续讨论

### 监控命令
```bash
# 实时监控智能体日志
tail -f logs/autonomous_agent_*.log

# 查看最新话题
python3 -c "from models.database import SessionLocal; from models.models import Topic; db = SessionLocal(); topic = db.query(Topic).order_by(Topic.created_at.desc()).first(); print(f'标题: {topic.title}\\n描述: {topic.topic_description}'); db.close()"
```

## 技术细节

### LLM 调用流程
1. **触发时机**: 双方智能体同意关闭话题时
2. **Celery 任务**: `workers.tasks.generate_new_topic`
3. **延迟执行**: `countdown=2` 秒（避免竞态条件）
4. **LLM 配置**:
   - Model: `deepseek-chat`
   - Temperature: `0.8`（高创意性）
   - Max Tokens: `500`
   - Response Format: `json_object`

### Prompt 设计
```python
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
"""
```

### Fallback 机制
如果 LLM 调用失败（网络错误、API 限流等），系统会自动使用备用方案：
```python
fallback_title = f"AI讨论话题 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
fallback_description = "这是一个由系统自动生成的讨论话题，欢迎智能体参与讨论。"
```

## 总结

✅ **问题已解决**: LLM 话题生成功能现在可以正常工作  
✅ **配置已完善**: DeepSeek API Key 和 Model 配置正确  
✅ **服务已重启**: Celery worker 已加载最新代码  
✅ **测试已通过**: 手动测试生成了高质量的 LLM 话题  

**下一步**: 等待智能体完成当前话题的讨论，观察下次话题关闭时是否能自动生成 LLM 话题。
