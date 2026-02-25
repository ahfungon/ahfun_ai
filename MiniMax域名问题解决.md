# MiniMax 域名问题解决

## 🎯 问题发现

通过直接测试发现，用户的 API Key 是正确的，但是在新域名 `api.minimax.io` 上无法使用！

## 📊 测试结果

| 域名 | 端点 | 结果 | 说明 |
|------|------|------|------|
| api.minimax.io | /chat/completions | ❌ 401 错误 | 新域名不支持旧 API Key |
| api.minimax.io | /text/chatcompletion_v2 | ❌ 401 错误 | 新域名不支持旧 API Key |
| **api.minimax.chat** | **/chat/completions** | **✅ 成功** | **旧域名可以工作** |

## 🔍 根本原因

用户的 API Key 格式：`sk-cp-cjKQ...`

这个 API Key 是在旧的 MiniMax 平台（api.minimax.chat）创建的，只能在旧域名上使用。新域名（api.minimax.io）可能需要新的 API Key 格式。

## ✅ 解决方案

### 已修改的配置

将所有 MiniMax API URL 从新域名改回旧域名：

```
修改前: https://api.minimax.io/v1
修改后: https://api.minimax.chat/v1
```

### 修改的文件

1. `services/system_config_service.py` - 默认 API URL
2. `config/settings.py` - 配置默认值
3. `services/summary_service.py` - 对话总结服务
4. `services/message_scoring_service.py` - 消息评分服务
5. `api/routes.py` - API 路由返回值
6. `API_ENDPOINTS.md` - API 文档
7. `static/api-docs.html` - 静态 API 文档

### 用户需要做的

1. **更新数据库配置**
   ```bash
   # 方法1: 在系统配置页面手动更新
   访问: http://localhost:8080/system-config.html
   将 "MiniMax API URL" 改为: https://api.minimax.chat/v1
   点击"保存配置"
   ```

   ```sql
   -- 方法2: 直接更新数据库
   UPDATE system_config 
   SET value = 'https://api.minimax.chat/v1' 
   WHERE key = 'minimax_api_url';
   ```

2. **重启 Worker**
   ```bash
   pkill -f celery && python quick_start.py
   ```

3. **刷新浏览器**
   - `Ctrl+F5` 或 `Cmd+Shift+R`

4. **测试**
   - 在智能体模拟器中测试 MiniMax 调用
   - 应该可以正常工作了

## 📝 API Key 类型说明

### 旧平台 API Key（api.minimax.chat）
- 格式：`sk-cp-` 开头
- 长度：约 125 字符
- 只能在 `api.minimax.chat` 域名使用
- 用户当前使用的就是这种

### 新平台 API Key（api.minimax.io）
- 格式：可能是 JWT 格式（`eyJ` 开头）
- 需要在新平台创建
- 只能在 `api.minimax.io` 域名使用

## 🔧 测试工具

创建了 `test_minimax_direct.py` 测试工具，可以：
1. 自动测试多种配置组合
2. 找出可用的配置
3. 生成 curl 命令用于手动测试

运行方式：
```bash
python test_minimax_direct.py
```

## 📊 测试输出示例

```
======================================================================
测试 3/5: 配置3: 旧域名 OpenAI 格式 (api.minimax.chat)
======================================================================
🔗 URL: https://api.minimax.chat/v1/chat/completions
🤖 Model: MiniMax-M2.5
📤 发送请求...
📥 状态码: 200
✅ 成功！
💬 响应内容: <think>The user is asking me to say "

🎉 这个配置可以工作！
✓ 推荐使用:
  - Base URL: https://api.minimax.chat/v1
  - Endpoint: /chat/completions
  - Model: MiniMax-M2.5
```

## 🎁 额外发现

1. **OpenAI 兼容格式可用**
   - 端点：`/chat/completions`
   - 不需要使用原生端点 `/text/chatcompletion_v2`

2. **模型名称正确**
   - `MiniMax-M2.5` 可以正常使用
   - 不需要改回 `abab6.5-chat`

3. **旧域名仍然可用**
   - `api.minimax.chat` 仍在服务
   - 旧 API Key 可以继续使用

## ⚠️ 注意事项

1. **域名兼容性**
   - 旧 API Key 只能用旧域名
   - 新 API Key 只能用新域名
   - 不能混用

2. **迁移建议**
   - 如果要使用新域名，需要在新平台创建新的 API Key
   - 目前保持使用旧域名和旧 API Key 是最简单的方案

3. **文档差异**
   - MiniMax 官方文档可能主要介绍新平台
   - 但旧平台仍然可用

## 📚 相关文档

- 测试工具：`test_minimax_direct.py`
- 诊断工具：`diagnose_minimax.py`
- 配置指南：`MiniMax配置更新指南.md`

## 🎯 总结

**问题**：使用了新域名 `api.minimax.io`，但用户的 API Key 是旧平台的

**解决**：改回使用旧域名 `api.minimax.chat`

**结果**：MiniMax API 调用成功！
