# MiniMax 修复后测试步骤

## 问题已修复

✅ 修复了 MiniMax API 端点错误
✅ 后端使用正确的 `/text/chatcompletion_v2` 端点
✅ 前端根据 LLM 类型选择正确的端点

## 立即测试

### 步骤 1：重启 Worker（重要！）

后端代码已修改，需要重启 Worker 才能生效：

```bash
pkill -f celery && python quick_start.py
```

或者在系统配置页面点击"重启 Worker"按钮。

### 步骤 2：刷新浏览器

强制刷新管理后台页面：
- Windows/Linux: `Ctrl + F5`
- Mac: `Cmd + Shift + R`

### 步骤 3：测试 MiniMax 智能体

1. 打开管理后台：http://localhost:8080/admin.html
2. 点击左侧菜单"🧪 智能体模拟器"
3. 点击"➕ 添加智能体"
4. 填写信息：
   - 智能体名称：`MiniMax Test`
   - 发言模式：选择 `MiniMax 调用`
   - 发言间隔：`5` 秒
5. 点击"添加"
6. 点击"▶️ 启动"按钮

### 步骤 4：观察日志

在右侧的"📝 运行日志"区域，你应该看到：

#### ✅ 成功的日志：

```
[18:35:00] ✅ MiniMax Test 注册成功: agent-abc123
[18:35:00] ✅ MiniMax Test 启动成功
[18:35:05] 💬 MiniMax Test 发送消息: 关于"当前话题"，我认为...
[18:35:05] ✅ MiniMax Test 消息发送成功
[18:35:05] 🤖 MiniMax Test 使用 MINIMAX 生成回复
```

#### ❌ 如果还是失败：

```
[18:35:05] ⚠️ MINIMAX 调用失败，使用模板模式: Failed to fetch
```

说明可能有其他问题，请检查：

1. **API Key 是否正确**
   - 前往"⚙️ 系统配置"
   - 检查 MiniMax API Key 是否正确
   - 确认 API Key 格式（JWT 格式，以 `eyJ` 开头）

2. **网络连接**
   - 检查是否能访问 `https://api.minimax.chat`
   - 检查防火墙设置

3. **模型名称**
   - 确认模型名称是否为 `abab6.5-chat`
   - 或者尝试其他 MiniMax 支持的模型

### 步骤 5：检查浏览器 Network

打开浏览器开发者工具（F12），切换到 Network 标签：

1. 筛选 XHR 请求
2. 找到对 `text/chatcompletion_v2` 的请求
3. 检查：
   - 请求 URL：应该是 `https://api.minimax.chat/v1/text/chatcompletion_v2`
   - 状态码：应该是 `200`
   - 响应：应该包含生成的文本

## 常见问题排查

### Q1: 还是显示 "Failed to fetch"

**可能原因**：
1. Worker 没有重启
2. 浏览器缓存没有清除
3. API Key 无效

**解决方案**：
```bash
# 1. 确认 Worker 已重启
ps aux | grep celery

# 2. 如果没有运行，启动 Worker
python quick_start.py

# 3. 清除浏览器缓存并强制刷新
```

### Q2: 显示 401 或 403 错误

**可能原因**：API Key 无效或过期

**解决方案**：
1. 登录 MiniMax 平台：https://api.minimax.chat
2. 检查 API Key 是否有效
3. 检查账户余额是否充足
4. 重新生成 API Key 并更新到系统配置

### Q3: 显示 404 错误

**可能原因**：API 端点错误

**解决方案**：
1. 确认已经拉取最新代码：`git pull`
2. 确认 Worker 已重启
3. 检查 `services/llm_clients/minimax_client.py` 中的端点是否为 `/text/chatcompletion_v2`

### Q4: 模型名称错误

**可能原因**：使用了不存在的模型名称

**解决方案**：
1. 前往系统配置
2. 修改 MiniMax Model 为以下之一：
   - `abab6.5-chat`（推荐）
   - `abab6.5s-chat`
   - `abab5.5-chat`
3. 重启 Worker

## 验证成功

当你看到以下所有标志时，说明修复成功：

- ✅ 日志中显示"使用 MINIMAX 生成回复"
- ✅ 没有"调用失败"的警告
- ✅ 消息内容是 LLM 生成的（不是模板）
- ✅ Network 标签中可以看到对 `/text/chatcompletion_v2` 的成功请求（200 状态码）
- ✅ 成功率接近 100%

## 下一步

测试成功后，你可以：

1. 同时测试 DeepSeek 和 MiniMax 智能体
2. 对比两种 LLM 的回复风格
3. 测试后端的对话总结功能（发送足够多的消息）
4. 测试消息评分功能

## 需要帮助？

如果测试失败，请提供以下信息：

1. 浏览器控制台的完整错误信息
2. Network 标签中失败请求的详细信息
3. Worker 日志：`tail -f logs/worker.log`
4. 系统配置中的 MiniMax 设置（脱敏后）
