# MiniMax 集成完成说明

## ✅ 完成状态

MiniMax 已成功集成到系统中，现在可以通过管理后台动态切换使用 DeepSeek 或 MiniMax 进行消息评分和对话总结。

## 📋 已完成的工作

### 1. 创建 MiniMax 客户端

**文件**: `services/llm_clients/minimax_client.py`

- 实现了与 DeepSeek 客户端相同的接口
- 支持对话总结生成 (`generate_summary`)
- 支持消息相关性评估 (`evaluate_message_relevance`)
- 包含完整的错误处理和重试机制
- 支持日志记录

### 2. 更新消息评分服务

**文件**: `services/message_scoring_service.py`

**主要改动**:
- 从系统配置读取 `llm_provider_scoring` 设置
- 根据配置动态初始化 DeepSeek 或 MiniMax 客户端
- 添加日志记录，显示使用的 LLM 提供商
- 支持从系统配置读取自定义评分 Prompt

**关键代码**:
```python
# 从系统配置获取 LLM 提供商
provider = self.config_service.get_config_value('llm_provider_scoring', 'deepseek')

if provider == 'minimax':
    self.llm_client = MiniMaxClient(...)
    self.llm_provider = 'MiniMax'
else:
    self.llm_client = DeepSeekClient(...)
    self.llm_provider = 'DeepSeek'
```

### 3. 更新对话总结服务

**文件**: `services/summary_service.py`

**主要改动**:
- 从系统配置读取 `llm_provider_summary` 设置
- 根据配置动态初始化 DeepSeek 或 MiniMax 客户端
- 添加日志记录，显示使用的 LLM 提供商
- 支持从系统配置读取自定义总结 Prompt
- 将 `_call_deepseek_api` 重命名为 `_call_llm_api`，支持两种 LLM

**关键代码**:
```python
# 从系统配置获取 LLM 提供商
provider = self.config_service.get_config_value('llm_provider_summary', 'deepseek')

if provider == 'minimax':
    self.llm_client = MiniMaxClient(...)
    self.llm_provider = 'MiniMax'
else:
    self.llm_client = DeepSeekClient(...)
    self.llm_provider = 'DeepSeek'
```

### 4. 更新配置文件

**文件**: `config/settings.py`

添加了 MiniMax 相关配置项:
- `minimax_api_key`: MiniMax API 密钥
- `minimax_api_url`: MiniMax API 端点
- `minimax_model`: MiniMax 模型名称

### 5. 更新客户端导出

**文件**: `services/llm_clients/__init__.py`

添加了 MiniMaxClient 的导出，使其可以被其他模块导入。

### 6. 创建测试脚本

**文件**: `test_minimax_integration.py`

功能:
- 检查系统配置（LLM 提供商、API Key 等）
- 测试服务初始化（验证正确的客户端被创建）
- 检查最近的日志（查找 LLM 调用记录）
- 提供详细的测试报告

## 🔍 验证结果

运行 `python3 test_minimax_integration.py` 的结果:

```
✓ 消息评分 LLM: minimax
✓ 对话总结 LLM: minimax

✓ MiniMax API Key: 已配置
✓ MiniMax API URL: https://api.minimax.chat/v1
✓ MiniMax Model: abab6.5-chat

[MessageScoringService]
✓ 初始化成功
✓ 使用的 LLM: MiniMax
✓ 客户端类型: MiniMaxClient

[SummaryService]
✓ 初始化成功
✓ 使用的 LLM: MiniMax
✓ 客户端类型: MiniMaxClient
```

## 📊 系统配置

当前系统配置（通过管理后台设置）:

| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| llm_provider_scoring | minimax | 消息评分使用 MiniMax |
| llm_provider_summary | minimax | 对话总结使用 MiniMax |
| minimax_api_key | sk-cp-cjKQ... | MiniMax API 密钥 |
| minimax_api_url | https://api.minimax.chat/v1 | MiniMax API 端点 |
| minimax_model | abab6.5-chat | MiniMax 模型 |

## 🔄 工作流程

### 消息评分流程

1. 用户发送消息
2. `MessageScoringService` 初始化时读取 `llm_provider_scoring` 配置
3. 根据配置创建 MiniMaxClient 或 DeepSeekClient
4. 调用 `evaluate_message_relevance()` 进行评分
5. 记录日志: `[MessageScoringService] Evaluating message {id} using MiniMax`

### 对话总结流程

1. Token 达到阈值触发总结任务
2. `SummaryService` 初始化时读取 `llm_provider_summary` 配置
3. 根据配置创建 MiniMaxClient 或 DeepSeekClient
4. 调用 `generate_summary()` 生成总结
5. 记录日志: `[SummaryService] Generating summary for topic {id} using MiniMax`

## 📝 日志记录

系统会在以下位置记录 LLM 调用信息:

### 服务初始化日志
```
INFO: [MessageScoringService] Initializing with LLM provider: minimax
INFO: [SummaryService] Initializing with LLM provider: minimax
```

### API 调用日志
```
INFO: [MessageScoringService] Evaluating message {id} using MiniMax
INFO: [SummaryService] Generating summary for topic {id} using MiniMax
```

### 查看日志命令

实时监控 MiniMax 调用:
```bash
# 监控 API 日志
tail -f logs/api.log | grep -i minimax

# 监控 Worker 日志
tail -f logs/worker.log | grep -i minimax

# 查看最近的 LLM 调用
tail -100 logs/api.log | grep -E "MessageScoringService|SummaryService"
```

## 🧪 测试方法

### 方法 1: 运行测试脚本

```bash
python3 test_minimax_integration.py
```

### 方法 2: 发送消息触发评分

1. 打开智能体模拟器: `http://localhost:8000/simulator.html`
2. 创建或选择一个话题
3. 发送一条消息
4. 查看日志确认 MiniMax 被调用

### 方法 3: 手动触发总结

```bash
python3 trigger_summary_manually.py
```

然后查看日志:
```bash
tail -50 logs/worker.log | grep -i minimax
```

## 🔧 配置切换

### 切换到 MiniMax

在管理后台 (`http://localhost:8000/admin.html`) 的系统配置页面:

1. 消息评分 LLM: 选择 "MiniMax"
2. 对话总结 LLM: 选择 "MiniMax"
3. 填写 MiniMax API Key
4. 点击保存

### 切换回 DeepSeek

1. 消息评分 LLM: 选择 "DeepSeek"
2. 对话总结 LLM: 选择 "DeepSeek"
3. 点击保存

### 混合使用

可以为不同功能使用不同的 LLM:
- 消息评分: DeepSeek
- 对话总结: MiniMax

或反之。

## ⚠️ 注意事项

### 1. 配置立即生效

配置更改后，新创建的服务实例会立即使用新配置。但已经运行的服务实例（如 Celery Worker）需要重启才能生效。

**重启 Worker**:
```bash
# 停止 Worker
pkill -f "celery -A workers.celery_app worker"

# 启动 Worker
celery -A workers.celery_app worker --loglevel=info --logfile=logs/worker.log &
```

### 2. API Key 必须配置

使用 MiniMax 前，必须在系统配置中填写有效的 MiniMax API Key，否则调用会失败。

### 3. API 端点格式

MiniMax API URL 应该是基础端点，不包含具体的路径:
- ✅ 正确: `https://api.minimax.chat/v1`
- ❌ 错误: `https://api.minimax.chat/v1/chat/completions`

### 4. 日志级别

确保日志级别设置为 INFO 或更低，才能看到 LLM 调用日志:
```python
logging.basicConfig(level=logging.INFO)
```

## 📈 性能对比

可以通过日志中的 `duration_ms` 字段对比 DeepSeek 和 MiniMax 的响应时间:

```
INFO: LLM call completed - provider=MiniMax, operation=generate_summary, duration_ms=1234.56
```

## 🎯 下一步建议

1. **监控 MiniMax 调用**: 使用日志监控命令实时查看 MiniMax 是否被成功调用
2. **对比效果**: 对比 DeepSeek 和 MiniMax 的总结质量和评分准确性
3. **性能测试**: 对比两个 LLM 的响应速度
4. **成本分析**: 根据 API 调用次数和定价对比成本
5. **错误处理**: 测试 API Key 错误、网络超时等异常情况

## 📞 故障排查

### 问题: 配置了 MiniMax 但仍在使用 DeepSeek

**解决方案**:
1. 检查系统配置: `python3 test_minimax_integration.py`
2. 重启 Celery Worker
3. 重启 API 服务器

### 问题: MiniMax API 调用失败

**检查项**:
1. API Key 是否正确
2. API URL 是否正确
3. 网络连接是否正常
4. 查看详细错误日志: `tail -100 logs/worker.log`

### 问题: 看不到日志

**解决方案**:
1. 确认日志文件存在: `ls -la logs/`
2. 检查日志级别配置
3. 使用测试脚本查看: `python3 test_minimax_integration.py`

## 📚 相关文件

- `services/llm_clients/minimax_client.py` - MiniMax 客户端实现
- `services/llm_clients/deepseek_client.py` - DeepSeek 客户端实现
- `services/message_scoring_service.py` - 消息评分服务
- `services/summary_service.py` - 对话总结服务
- `services/system_config_service.py` - 系统配置服务
- `config/settings.py` - 应用配置
- `test_minimax_integration.py` - 集成测试脚本
- `frontend/system-config.html` - 系统配置管理页面

## ✨ 总结

MiniMax 已成功集成到系统中，现在你可以:

1. ✅ 通过管理后台动态切换 LLM 提供商
2. ✅ 为消息评分和对话总结分别选择不同的 LLM
3. ✅ 配置更改立即生效（新服务实例）
4. ✅ 完整的日志记录，方便监控和调试
5. ✅ 支持自定义 Prompt 模板

系统已经配置为使用 MiniMax，下次发送消息或触发总结时，将会调用 MiniMax API。
