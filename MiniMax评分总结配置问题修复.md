# MiniMax 评分和总结配置问题修复

## 问题描述

用户在系统配置中设置了使用 MiniMax 进行消息评分和对话总结，但没有生效。

## 问题诊断

### 1. 运行诊断脚本
```bash
python diagnose_llm_provider.py
```

**发现问题：**
```
API URL: https://api.minimaxi.com/v1  ❌ 错误
```

**正确的 URL：**
```
API URL: https://api.minimax.chat/v1  ✅ 正确
```

### 2. 根本原因

用户的 API Key 格式是 `sk-cp-cjKQ...`（旧平台格式），只能在旧域名 `api.minimax.chat` 使用，不能在新域名 `api.minimaxi.com` 使用。

用户在系统配置中错误地填写了新域名，导致 API 调用失败。

---

## 解决方案

### 方法 1：使用修复脚本（推荐）

```bash
python fix_minimax_url.py
```

**输出：**
```
修复为: https://api.minimax.chat/v1
✅ URL 已更新

⚠️ 重要: 需要重启 Worker 才能生效
重启命令: bash restart_worker_quick.sh
```

### 方法 2：手动修复

1. 访问系统配置页面：http://localhost:8080/system-config.html
2. 找到 "MiniMax API URL" 配置项
3. 修改为：`https://api.minimax.chat/v1`
4. 点击"保存配置"
5. 重启 Worker：`bash restart_worker_quick.sh`

---

## 重启 Worker

**重要：** 修改配置后必须重启 Worker 才能生效！

```bash
bash restart_worker_quick.sh
```

或在系统配置页面点击"重启 Worker"按钮。

---

## 验证修复

### 1. 运行诊断脚本
```bash
python diagnose_llm_provider.py
```

**预期输出：**
```
1. 消息评分 LLM 配置
------------------------------------------------------------
提供商: minimax
API Key: sk-cp-cjKQ...
API URL: https://api.minimax.chat/v1  ✅
模型: MiniMax-M2.5
✅ MiniMax API Key 已配置

2. 对话总结 LLM 配置
------------------------------------------------------------
提供商: minimax
API Key: sk-cp-cjKQ...
API URL: https://api.minimax.chat/v1  ✅
模型: MiniMax-M2.5
✅ MiniMax API Key 已配置

3. Worker 状态检查
------------------------------------------------------------
✅ Worker 正在运行
```

### 2. 测试消息评分

发送一条消息，检查是否有评分：

```bash
# 查看最新消息的评分
curl http://localhost:8080/api/monitor/topic/active/messages | jq '.messages[0].relevance_score'
```

如果返回数字（如 85.0），说明评分功能正常。

### 3. 测试对话总结

发送足够多的消息（达到 token 阈值），检查是否生成总结。

---

## 常见问题

### Q1: 为什么 URL 会错误？

**A:** 用户可能在系统配置中手动填写了新域名 `api.minimaxi.com`，但这个域名只支持新格式的 API Key（`sk-xxx` 格式）。

旧格式的 API Key（`sk-cp-xxx` 格式）只能在旧域名 `api.minimax.chat` 使用。

### Q2: 如何判断我的 API Key 是新格式还是旧格式？

**A:** 查看 API Key 的前缀：
- 旧格式：`sk-cp-xxx...`（需要使用 `api.minimax.chat`）
- 新格式：`sk-xxx...`（可以使用 `api.minimaxi.com`）

### Q3: 修改配置后为什么没有立即生效？

**A:** Worker 在启动时读取配置，修改配置后必须重启 Worker 才能生效。

```bash
bash restart_worker_quick.sh
```

### Q4: 如何确认 MiniMax 正在被使用？

**A:** 查看 Worker 日志：

```bash
tail -f logs/worker.log | grep -i minimax
```

应该看到类似的日志：
```
[SummaryService] Initializing with LLM provider: minimax
[MessageScoringService] Initializing with LLM provider: minimax
```

---

## 技术细节

### 配置读取流程

1. **Worker 启动时：**
   ```python
   # services/summary_service.py
   provider = self.config_service.get_config_value('llm_provider_summary', 'deepseek')
   
   if provider == 'minimax':
       api_url = self.config_service.get_config_value('minimax_api_url', 'https://api.minimax.chat/v1')
       # 使用配置的 URL
   ```

2. **配置优先级：**
   - 系统配置（数据库）> 默认值
   - 如果数据库中有配置，使用数据库的值
   - 如果数据库中没有，使用默认值

3. **为什么需要重启 Worker：**
   - Worker 在启动时初始化 LLM 客户端
   - LLM 客户端在初始化时读取配置
   - 修改配置后，已运行的 Worker 不会自动重新读取
   - 必须重启 Worker 才能使用新配置

### 域名对应关系

| API Key 格式 | 域名 | 说明 |
|-------------|------|------|
| `sk-cp-xxx...` | `api.minimax.chat` | 旧平台，旧格式 Key |
| `sk-xxx...` | `api.minimaxi.com` | 新平台，新格式 Key |

**注意：** 不能混用！旧 Key 只能用旧域名，新 Key 只能用新域名。

---

## 预防措施

### 1. 在系统配置页面添加提示

建议在 MiniMax API URL 配置项旁边添加说明：

```
提示：
- 旧格式 API Key (sk-cp-xxx): 使用 https://api.minimax.chat/v1
- 新格式 API Key (sk-xxx): 使用 https://api.minimaxi.com/v1
```

### 2. 添加配置验证

在保存配置时验证 API Key 和 URL 的匹配：

```python
def validate_minimax_config(api_key, api_url):
    if api_key.startswith('sk-cp-') and 'minimaxi.com' in api_url:
        raise ValueError("旧格式 API Key 不能使用新域名")
    if not api_key.startswith('sk-cp-') and 'minimax.chat' in api_url:
        raise ValueError("新格式 API Key 不能使用旧域名")
```

### 3. 添加健康检查

定期检查 LLM API 是否可用：

```python
# 在 Worker 启动时测试 API 连接
try:
    test_response = llm_client.test_connection()
    logger.info(f"✅ {provider} API 连接正常")
except Exception as e:
    logger.error(f"❌ {provider} API 连接失败: {e}")
```

---

## 相关文件

### 诊断工具
- `diagnose_llm_provider.py` - 诊断 LLM 提供商配置
- `fix_minimax_url.py` - 修复 MiniMax API URL

### 服务代码
- `services/summary_service.py` - 对话总结服务
- `services/message_scoring_service.py` - 消息评分服务
- `services/system_config_service.py` - 系统配置服务

### 配置文件
- 系统配置（数据库）- 通过系统配置页面管理

---

## 总结

### 问题
- MiniMax API URL 配置错误（使用了新域名但 API Key 是旧格式）
- Worker 没有重启，配置未生效

### 解决
1. ✅ 修复 API URL 为 `https://api.minimax.chat/v1`
2. ✅ 重启 Worker
3. ✅ 验证配置正确

### 结果
- ✅ MiniMax 现在可以正常用于消息评分
- ✅ MiniMax 现在可以正常用于对话总结
- ✅ 配置已验证正确

---

**重要提醒：** 每次修改 LLM 相关配置后，都必须重启 Worker！
