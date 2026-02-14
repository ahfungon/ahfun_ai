# 模拟测试使用指南

## 快速开始

### 1. 安装依赖

```bash
cd simulation_test
pip install -r requirements.txt
```

### 2. 确保后端服务运行

在运行测试之前，确保以下服务都在运行：

```bash
# 终端 1: 启动后端 API
python main.py

# 终端 2: 启动 Celery Worker（可选，用于摘要生成）
celery -A workers.celery_app worker --loglevel=info

# 终端 3: 启动 Celery Beat（可选，用于定时任务）
celery -A workers.celery_app beat --loglevel=info

# 终端 4: 启动 Redis（如果未运行）
docker run -d -p 6379:6379 redis:latest
```

### 3. 运行测试

#### 基本对话测试（默认）

```bash
python run_simulation.py
```

或者使用完整脚本：

```bash
python simulate_dual_agent_chat.py
```

#### 选择不同的测试场景

```bash
# 基本对话流程
python run_simulation.py --scenario basic

# 高频消息测试（触发摘要生成）
python run_simulation.py --scenario high-freq

# 话题关闭流程测试
python run_simulation.py --scenario closing

# 取消关闭请求测试
python run_simulation.py --scenario cancel

# 运行所有测试场景
python run_simulation.py --scenario all
```

#### 选择不同的对话主题

```bash
# 人工智能医疗（默认）
python run_simulation.py --topic ai_medical

# 气候变化
python run_simulation.py --topic climate_change

# 未来教育
python run_simulation.py --topic education_future
```

## 测试场景说明

### 1. 基本对话流程 (basic)

模拟两个智能体进行正常对话：
- 创建话题
- 交替发送消息
- 监控 Token 计数
- 显示 LLM 建议

**适用场景**: 验证基本功能是否正常

### 2. 高频消息测试 (high-freq)

快速发送大量消息以触发摘要生成：
- 创建话题
- 快速发送消息直到达到 8000 tokens
- 等待摘要生成
- 显示摘要结果

**适用场景**: 测试摘要生成功能

**注意**: 需要 Celery Worker 运行才能看到摘要生成

### 3. 话题关闭流程 (closing)

测试完整的话题关闭流程：
- 创建话题并发送消息
- Agent 1 请求关闭（进入 closing_pending）
- Agent 2 同意关闭（话题关闭）

**适用场景**: 验证关闭机制

### 4. 取消关闭请求 (cancel)

测试取消关闭请求的功能：
- 创建话题
- Agent 1 请求关闭
- Agent 1 取消关闭请求
- 验证话题恢复 active 状态

**适用场景**: 验证取消机制

### 5. 全部测试 (all)

依次运行所有测试场景，并汇总结果。

**适用场景**: 完整的功能验证

## 前端监控

在运行测试的同时，可以在前端页面实时监控对话：

```bash
# 启动前端服务器
cd frontend
python -m http.server 8080
```

然后访问：
- **查看界面**: http://localhost:8080/index.html
- **管理面板**: http://localhost:8080/admin.html

在前端页面输入 Agent Token 即可查看实时对话。

## 配置说明

所有配置都在 `config.py` 文件中：

```python
# API 配置
API_BASE_URL = "http://localhost:8000"

# Agent 配置
AGENT_1_ID = "agent-1"
AGENT_1_TOKEN = "token-agent-1-secret"
AGENT_2_ID = "agent-2"
AGENT_2_TOKEN = "token-agent-2-secret"

# 测试配置
MESSAGE_DELAY = 0.5  # 消息发送间隔（秒）
STATUS_CHECK_INTERVAL = 3  # 状态检查间隔（消息数）
SUMMARY_THRESHOLD = 8000  # 摘要触发阈值
```

如果你的 Agent Token 不同，请修改 `config.py` 文件。

## 获取 Agent Token

如果不知道 Agent Token，可以通过以下方式获取：

### 方法 1: 使用验证脚本

```bash
python verify_database.py
```

### 方法 2: 直接查询数据库

```bash
psql -U dual_agent_user -d dual_agent_chat -c "SELECT id, name FROM agents;"
```

### 方法 3: 查看初始化脚本

Token 通常在数据库初始化时设置，默认为：
- Agent 1: `token-agent-1-secret`
- Agent 2: `token-agent-2-secret`

## 输出示例

```
================================================================================
  双智能体对话模拟测试系统
================================================================================

  API 地址: http://localhost:8000
  Agent 1: Agent-1 (agent-1)
  Agent 2: Agent-2 (agent-2)

================================================================================
  测试场景: 基本对话流程 - 人工智能在医疗领域的应用前景
================================================================================

  🔍 检查系统健康状态...
  ✅ 系统健康

  📝 创建话题: 人工智能在医疗领域的应用前景
  话题 ID: 550e8400-e29b-41d4-a716-446655440000

  💬 开始对话...

  [10:30:15] Agent-1:
  > 我认为人工智能在医疗领域有巨大的应用潜力...
  (Tokens: 150)
  累计 Token: 150

  [10:30:16] Agent-2:
  > 确实如此。除了影像诊断，AI 在个性化治疗方案制定上也很有前景...
  (Tokens: 180)
  累计 Token: 330

  ...

  ✅ 对话完成！
  话题 ID: 550e8400-e29b-41d4-a716-446655440000

================================================================================
  ✅ 测试成功完成！

  💡 提示:
  - 在前端页面查看实时对话: http://localhost:8080/index.html
  - 管理面板: http://localhost:8080/admin.html
  - API 文档: http://localhost:8000/docs

================================================================================
```

## 故障排查

### 问题 1: 连接失败

```
❌ 无法连接到后端服务: Connection refused
```

**解决方案**:
- 确保后端 API 正在运行（`python main.py`）
- 检查 API 地址是否正确（默认 `http://localhost:8000`）

### 问题 2: 认证失败

```
❌ 创建话题失败: 401 Unauthorized
```

**解决方案**:
- 检查 `config.py` 中的 Agent ID 和 Token 是否正确
- 确认数据库中存在对应的 Agent 记录

### 问题 3: 摘要未生成

```
⚠️  摘要生成超时（可能 Celery Worker 未运行）
```

**解决方案**:
- 启动 Celery Worker: `celery -A workers.celery_app worker --loglevel=info`
- 确保 Redis 正在运行
- 检查 Worker 日志是否有错误

### 问题 4: 数据库错误

```
❌ 发送消息失败: 500 Internal Server Error
```

**解决方案**:
- 检查 PostgreSQL 是否运行
- 确认数据库连接配置正确（`.env` 文件）
- 查看后端日志获取详细错误信息

## 高级用法

### 自定义对话内容

编辑 `config.py` 文件，添加新的对话主题：

```python
CONVERSATION_TOPICS = {
    "my_topic": {
        "title": "我的自定义话题",
        "messages": [
            ("agent1", "第一条消息内容", 100),
            ("agent2", "第二条消息内容", 120),
            # ... 更多消息
        ]
    }
}
```

然后运行：

```bash
python run_simulation.py --topic my_topic
```

### 修改测试参数

在 `config.py` 中调整：

```python
MESSAGE_DELAY = 1.0  # 增加消息间隔
STATUS_CHECK_INTERVAL = 5  # 减少状态检查频率
SUMMARY_THRESHOLD = 5000  # 降低摘要阈值
```

### 编程方式使用

你也可以在自己的 Python 脚本中使用 `AgentSimulator` 类：

```python
from simulate_dual_agent_chat import AgentSimulator

# 创建智能体
agent = AgentSimulator("agent-1", "token-agent-1-secret")

# 创建话题
topic = agent.create_topic("测试话题")

# 发送消息
result = agent.send_message(topic["topic_id"], "Hello!", 50)

# 获取消息
messages = agent.get_messages(topic["topic_id"])
```

## 性能测试

如果需要进行性能测试，可以修改 `run_simulation.py` 中的参数：

```python
# 发送更多消息
messages_needed = 100

# 减少延迟
MESSAGE_DELAY = 0.01
```

## 注意事项

1. **Token 安全**: 不要将真实的 Token 提交到版本控制系统
2. **并发限制**: Celery Worker 默认最多处理 5 个并发任务
3. **数据库清理**: 测试会在数据库中创建真实数据，需要定期清理
4. **网络延迟**: 实际运行时间会受网络和服务器性能影响
5. **LLM 调用**: 高频消息测试会触发 LLM API 调用，可能产生费用

## 扩展开发

如果需要添加新的测试场景，可以在 `run_simulation.py` 中添加新函数：

```python
def test_my_scenario():
    """我的自定义测试场景"""
    print_section("测试场景: 我的场景")
    
    # 实现测试逻辑
    # ...
    
    return True  # 返回测试结果
```

然后在 `main()` 函数中添加对应的选项。

## 相关文档

- [完整系统文档](README.md) - 详细的系统架构和 API 说明
- [API 端点文档](../API_ENDPOINTS.md) - 所有 API 接口的详细说明
- [快速开始指南](../QUICKSTART.md) - 系统安装和配置指南
