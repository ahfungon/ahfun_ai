# MiniMax API Key 问题解决指南

## 🔍 问题诊断结果

运行诊断工具发现：**API Key 无效（错误代码 2049）**

```
❌ 认证失败：API Key 无效或过期
响应: {"type":"error","error":{"type":"authorized_error","message":"invalid api key (2049)"}}
```

## 🎯 根本原因

你当前配置的 API Key 是：`sk-cp-cjKQ...`

这是 **DeepSeek 的 API Key 格式**，不是 MiniMax 的！

## 🔑 API Key 格式对比

| LLM 提供商 | API Key 格式 | 示例 |
|-----------|-------------|------|
| **DeepSeek** | 以 `sk-` 开头 | `sk-1234567890abcdef...` |
| **MiniMax** | JWT 格式，以 `eyJ` 开头 | `eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...` |
| **OpenAI** | 以 `sk-` 或 `sk-proj-` 开头 | `sk-proj-1234567890...` |

## ✅ 解决步骤

### 步骤 1：获取正确的 MiniMax API Key

1. **访问 MiniMax 平台**
   - 网址：https://platform.minimax.io
   - 或：https://platform.minimaxi.com

2. **登录账号**
   - 如果没有账号，先注册

3. **创建 API Key**
   - 进入 API Keys 或密钥管理页面
   - 点击"创建新密钥"或"Create API Key"
   - 复制生成的 API Key

4. **识别正确的 API Key**
   - MiniMax API Key 通常很长（几百个字符）
   - 可能以 `eyJ` 开头（JWT 格式）
   - **绝对不是** `sk-` 开头

### 步骤 2：更新系统配置

1. **打开系统配置页面**
   ```
   http://localhost:8080/system-config.html
   ```

2. **找到 MiniMax API Key 配置项**
   - 在"LLM 配置"部分
   - 标题是"MiniMax API Key"

3. **粘贴正确的 API Key**
   - 删除旧的 `sk-cp-cjKQ...`
   - 粘贴从 MiniMax 平台复制的新 API Key
   - 确保没有多余的空格或换行

4. **保存配置**
   - 点击"保存配置"按钮
   - 等待提示"配置保存成功"

### 步骤 3：重启 Worker

**方法 1：使用系统配置页面**
- 在系统配置页面点击"重启 Worker"按钮
- 等待 10-15 秒

**方法 2：使用命令行**
```bash
pkill -f celery && python quick_start.py
```

### 步骤 4：验证配置

运行诊断工具验证：
```bash
python diagnose_minimax.py
```

**成功的输出**：
```
✅ MiniMax API 调用成功！
✓ 响应内容: Hello! How can I assist you?...
```

**如果还是失败**：
- 检查 API Key 是否完整复制
- 检查 API Key 是否有效（未过期）
- 检查账户余额是否充足

### 步骤 5：测试智能体

1. **刷新浏览器**
   - 强制刷新：`Ctrl+F5` (Windows) 或 `Cmd+Shift+R` (Mac)

2. **进入智能体模拟器**
   - 访问：http://localhost:8080/admin.html
   - 点击"智能体模拟器"

3. **添加 MiniMax 智能体**
   - 点击"添加智能体"
   - 发言模式选择"MiniMax 调用"
   - 启动智能体

4. **观察日志**
   - 应该看到：`✅ MiniMax Agent 启动成功`
   - 应该看到：`🤖 使用 MINIMAX 生成回复`

## 🆘 常见问题

### Q1: 我没有 MiniMax 账号怎么办？

**答**：
1. 访问 https://platform.minimax.io 注册
2. 完成实名认证（如果需要）
3. 充值账户（如果需要）
4. 创建 API Key

### Q2: 我找不到 MiniMax API Key 在哪里创建？

**答**：
1. 登录 MiniMax 平台
2. 查找以下菜单：
   - "API Keys"
   - "密钥管理"
   - "开发者设置"
   - "Settings" -> "API Keys"
3. 如果找不到，联系 MiniMax 客服

### Q3: 我确定 API Key 是对的，但还是 401 错误？

**答**：可能的原因：
1. **API Key 已过期** - 重新生成一个
2. **账户余额不足** - 充值账户
3. **API Key 权限不足** - 检查权限设置
4. **复制时包含空格** - 重新复制，确保没有多余字符
5. **API Key 被禁用** - 在平台上检查状态

### Q4: DeepSeek 和 MiniMax 可以同时使用吗？

**答**：可以！它们是独立的配置：
- **DeepSeek API Key** - 配置在"DeepSeek API Key"
- **MiniMax API Key** - 配置在"MiniMax API Key"

不同的智能体可以选择不同的 LLM。

### Q5: 如何知道我的 API Key 是哪个平台的？

**答**：根据格式判断：
- `sk-` 开头 → DeepSeek 或 OpenAI
- `eyJ` 开头 → MiniMax（JWT 格式）
- 很长的随机字符串 → 可能是 MiniMax

## 📊 诊断工具使用

### 运行诊断
```bash
python diagnose_minimax.py
```

### 诊断内容
1. ✓ 检查系统配置（API Key、URL、模型）
2. ✓ 验证配置格式
3. ✓ 测试网络连接
4. ✓ 测试 API 调用

### 输出解读

**成功**：
```
✅ MiniMax API 调用成功！
✓ 响应内容: Hello! How can I assist you?...
```

**失败**：
```
❌ 认证失败：API Key 无效或过期
❌ 网络连接失败：无法连接到 API
❌ 端点不存在：API URL 或端点路径错误
```

## 🔧 快速修复清单

- [ ] 确认使用的是 MiniMax 的 API Key（不是 DeepSeek 的）
- [ ] 确认 API Key 格式正确（通常以 `eyJ` 开头）
- [ ] 确认 API Key 完整复制（没有截断或多余空格）
- [ ] 确认 API URL 是 `https://api.minimax.io/v1`
- [ ] 确认模型名称是 `MiniMax-M2.5`
- [ ] 重启了 Worker
- [ ] 刷新了浏览器
- [ ] 运行诊断工具验证

## 📞 需要帮助？

如果按照以上步骤仍然无法解决，请提供：

1. **诊断工具输出**
   ```bash
   python diagnose_minimax.py > minimax_diagnosis.txt
   ```

2. **浏览器控制台错误**
   - 打开 F12 开发者工具
   - Console 标签的错误信息
   - Network 标签中失败请求的详细信息

3. **系统配置截图**
   - 脱敏后的配置（隐藏 API Key 的大部分内容）

4. **MiniMax 平台信息**
   - 账户状态
   - API Key 状态
   - 余额情况

## 🎯 总结

**问题**：使用了 DeepSeek 的 API Key 而不是 MiniMax 的

**解决**：
1. 从 MiniMax 平台获取正确的 API Key
2. 在系统配置中更新
3. 重启 Worker
4. 测试验证

**验证**：运行 `python diagnose_minimax.py` 应该显示成功
