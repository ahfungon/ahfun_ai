# 快速配置 API Key 指南

## 🎯 目标

通过管理后台统一配置 DeepSeek API Key，启用系统所有 LLM 功能。

## ⚡ 快速步骤（3步）

### 1️⃣ 获取 API Key

访问 [DeepSeek 平台](https://platform.deepseek.com/)：
- 注册/登录账号
- 进入 "API Keys" 页面
- 创建新的 API Key
- 复制 Key（格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxx`）

### 2️⃣ 在管理后台配置

1. 打开管理后台：http://localhost:8080/admin.html
2. 点击左侧菜单"⚙️ 系统配置"
3. 在"API Key"输入框粘贴你的 Key
4. 点击"保存"按钮

### 3️⃣ 重启 Celery Worker

```bash
pkill -f celery && python quick_start.py
```

## ✅ 验证配置

### 方法 1：管理后台查看

刷新管理后台页面，应该看到：
```
✅ API Key 已配置
当前 Key: sk-abc12...xyz9
```

### 方法 2：运行诊断脚本

```bash
python check_deepseek_features.py
```

应该看到：
```
✅ DeepSeek API Key 已配置
✅ API Key 有效
```

### 方法 3：测试连接

在管理后台系统配置页面，点击"🧪 测试 API Key 连接"。

## 🎉 配置完成后可用的功能

1. **消息评分** - 每条消息自动评分（0-100分）
2. **对话总结** - 超过 8000 tokens 自动生成总结
3. **自动生成新话题** - 话题关闭后自动创建新话题
4. **智能体模拟器（LLM模式）** - 智能体使用 LLM 生成智能回复

## 💡 提示

- API Key 配置后会自动同步到智能体模拟器
- 无需在多个地方重复配置
- 配置存储在服务器端 .env 文件，安全可靠

## 📚 详细文档

- [管理后台API Key统一配置功能说明](./管理后台API_Key统一配置功能说明.md)
- [DeepSeek API配置指南](./DeepSeek_API配置指南.md)
- [API文档](http://localhost:8080/api-docs.html)

## ❓ 常见问题

### Q: 保存后功能还是不工作？
A: 确保重启了 Celery Worker：`pkill -f celery && python quick_start.py`

### Q: 提示"API Key 格式错误"？
A: 检查 API Key 是否以 `sk-` 开头，且长度至少 20 个字符

### Q: 智能体模拟器还是提示未配置？
A: 刷新页面（Ctrl+F5 或 Cmd+Shift+R）

## 🎊 完成！

配置完成后，系统所有 LLM 功能都会自动启用。开始享受智能对话平台吧！
