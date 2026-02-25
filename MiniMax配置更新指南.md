# MiniMax 配置更新指南

## 🎯 重要更新

根据 MiniMax 官方文档，我们已将 MiniMax 集成更新为使用 **OpenAI 兼容格式**，并使用最新的 **MiniMax-M2.5** 模型。

## ⚡ 快速更新步骤

### 步骤 1：更新系统配置（必须！）

打开系统配置页面：http://localhost:8080/system-config.html

找到并更新以下两项：

1. **MiniMax API URL**
   - 旧值: `https://api.minimax.chat/v1`
   - 新值: `https://api.minimax.io/v1`

2. **MiniMax 模型**
   - 旧值: `abab6.5-chat`
   - 新值: `MiniMax-M2.5`

点击"保存配置"按钮。

### 步骤 2：重启 Worker（必须！）

在系统配置页面点击"重启 Worker"按钮，或运行：

```bash
pkill -f celery && python quick_start.py
```

等待 10-15 秒让 Worker 完全启动。

### 步骤 3：刷新浏览器

强制刷新管理后台页面：
- Windows/Linux: `Ctrl + F5`
- Mac: `Cmd + Shift + R`

### 步骤 4：测试 MiniMax

1. 进入"智能体模拟器"
2. 添加使用 "MiniMax 调用" 的智能体
3. 启动并观察日志

## ✅ 预期结果

日志应该显示：

```
✅ MiniMax Agent 启动成功
💬 MiniMax Agent 发送消息: ...
✅ MiniMax Agent 消息发送成功
🤖 MiniMax Agent 使用 MINIMAX 生成回复
```

## 🔍 验证更新

### 方法 1：检查浏览器 Network

打开开发者工具（F12），Network 标签：
- 请求 URL 应该是: `https://api.minimax.io/v1/chat/completions`
- 请求体中的 model 应该是: `MiniMax-M2.5`
- 状态码应该是: `200`

### 方法 2：检查数据库

```bash
python -c "
from models.database import SessionLocal
from services.system_config_service import SystemConfigService

db = SessionLocal()
service = SystemConfigService(db)

print('MiniMax API URL:', service.get_config_value('minimax_api_url'))
print('MiniMax Model:', service.get_config_value('minimax_model'))

db.close()
"
```

应该输出：
```
MiniMax API URL: https://api.minimax.io/v1
MiniMax Model: MiniMax-M2.5
```

## 🎨 可选：使用极速版

如果需要更快的响应速度，可以使用极速版模型：

在系统配置中将 "MiniMax 模型" 改为：
- `MiniMax-M2.5-highspeed`（输出速度 ~100 TPS）

然后重启 Worker。

## 📊 模型对比

| 模型 | 上下文 | 速度 | 适用场景 |
|------|--------|------|---------|
| MiniMax-M2.5 | 204,800 | ~60 TPS | 平衡性能和成本（推荐） |
| MiniMax-M2.5-highspeed | 204,800 | ~100 TPS | 需要快速响应 |
| MiniMax-M2.1 | 204,800 | ~60 TPS | 多语言编程 |
| MiniMax-M2 | 204,800 | ~60 TPS | Agent 工作流 |

## ❓ 常见问题

### Q: 更新后还是失败怎么办？

**检查清单**：
1. ✅ 系统配置中的 API URL 是否为 `https://api.minimax.io/v1`
2. ✅ 系统配置中的模型是否为 `MiniMax-M2.5`
3. ✅ Worker 是否已重启
4. ✅ 浏览器是否已强制刷新
5. ✅ API Key 是否有效（未过期、有余额）

### Q: API Key 需要重新申请吗？

**答**：不需要！旧的 API Key 仍然有效，只需要更新 API URL 和模型名称。

### Q: 为什么要改用 OpenAI 兼容格式？

**答**：
- 官方推荐的标准格式
- 与 DeepSeek 使用相同格式，代码更统一
- 支持最新的 MiniMax-M2.5 模型
- 更好的生态系统支持

### Q: 旧的配置会自动更新吗？

**答**：不会！必须手动更新系统配置中的 API URL 和模型名称。

## 📚 相关文档

- [MiniMax OpenAI 兼容 API 文档](https://platform.minimax.io/docs/api-reference/text-openai-api)
- [详细修复说明](./MiniMax_OpenAI兼容格式修复.md)
- [测试步骤](./MiniMax修复后测试步骤.md)

## 🆘 需要帮助？

如果更新后仍有问题，请提供：
1. 系统配置截图（脱敏 API Key）
2. 浏览器控制台错误信息
3. Worker 日志：`tail -f logs/worker.log`
4. Network 标签中失败请求的详细信息
