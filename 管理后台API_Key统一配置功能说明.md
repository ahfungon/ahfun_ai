# 管理后台 API Key 统一配置功能说明

## 功能概述

在管理后台新增了"⚙️ 系统配置"页面，允许管理员统一配置 DeepSeek API Key。配置后的 API Key 将用于：

1. **消息评分功能** - 自动评估消息相关性
2. **对话总结功能** - 定期生成对话总结和建议
3. **自动生成新话题** - 话题关闭后自动创建新话题
4. **智能体模拟器（LLM模式）** - 智能体使用 LLM 生成回复

## 功能特点

### 1. 统一管理
- 一次配置，全系统使用
- 无需在多个地方重复配置
- 智能体模拟器自动同步系统配置

### 2. 安全性
- API Key 存储在服务器端 .env 文件
- 前端显示时自动掩码（只显示前8位和后4位）
- 输入框使用密码类型，防止泄露

### 3. 实时验证
- 输入时验证 API Key 格式
- 保存前检查长度和前缀
- 提供测试连接功能

### 4. 友好提示
- 配置状态一目了然（已配置/未配置）
- 更新后提示需要重启 Celery Worker
- 提供配置文档和获取 API Key 的链接

## 使用方法

### 步骤 1：进入系统配置

1. 打开管理后台：`http://localhost:8080/admin.html`
2. 点击左侧菜单的"⚙️ 系统配置"

### 步骤 2：配置 API Key

1. 访问 [DeepSeek 平台](https://platform.deepseek.com/) 获取 API Key
2. 在"API Key"输入框中粘贴你的 API Key（格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxx`）
3. 点击"保存"按钮
4. 确认保存提示

### 步骤 3：重启 Celery Worker

配置更新后，需要重启 Celery Worker 使新配置生效：

```bash
pkill -f celery && python quick_start.py
```

### 步骤 4：验证配置

1. 刷新页面，查看配置状态是否显示"✅ API Key 已配置"
2. 点击"🧪 测试 API Key 连接"验证连接
3. 或运行诊断脚本：`python check_deepseek_features.py`

## API 端点

### 1. 获取 API Key 状态

```http
GET /api/admin/config/api-key
```

**响应示例：**
```json
{
  "is_configured": true,
  "masked_key": "sk-abc12...xyz9",
  "api_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat"
}
```

### 2. 更新 API Key

```http
POST /api/admin/config/api-key
Content-Type: application/json

{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**成功响应：**
```json
{
  "success": true,
  "message": "API Key updated successfully. Please restart Celery Worker to apply changes.",
  "restart_required": true
}
```

**错误响应：**
```json
{
  "detail": "Invalid API Key format (should start with 'sk-')"
}
```

## 验证规则

系统会对输入的 API Key 进行以下验证：

1. **非空检查**：API Key 不能为空
2. **格式检查**：必须以 `sk-` 开头
3. **长度检查**：至少 20 个字符

## 智能体模拟器集成

### 自动同步

当在系统配置中更新 API Key 后，智能体模拟器会自动同步该配置：

1. 系统配置保存 API Key 到 .env 文件
2. 同时保存到浏览器 localStorage（供模拟器使用）
3. 模拟器启动时自动加载系统配置的 API Key

### 独立配置（可选）

如果需要，智能体模拟器仍然支持独立配置 API Key：

1. 点击模拟器页面的"⚙️ 配置API Key"按钮
2. 输入独立的 API Key（仅用于模拟器）
3. 此配置不影响系统其他功能

**推荐做法：** 使用系统配置统一管理，避免重复配置。

## 配置文件更新

API Key 配置会直接更新 `.env` 文件：

**更新前：**
```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

**更新后：**
```bash
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

## 安全注意事项

1. **不要分享 API Key**：API Key 是敏感信息，不要在公开场合分享
2. **定期轮换**：建议定期更换 API Key
3. **监控使用量**：在 DeepSeek 平台监控 API 使用量和费用
4. **备份配置**：更新前建议备份 .env 文件

## 故障排查

### 问题 1：保存后功能仍不工作

**原因：** 未重启 Celery Worker

**解决：**
```bash
pkill -f celery && python quick_start.py
```

### 问题 2：提示"API Key 格式错误"

**原因：** API Key 格式不正确

**解决：**
- 确保 API Key 以 `sk-` 开头
- 确保完整复制了整个 API Key
- 检查是否有多余的空格或换行符

### 问题 3：测试连接失败

**原因：** API Key 无效或网络问题

**解决：**
- 在 DeepSeek 平台检查 API Key 是否有效
- 检查网络连接
- 查看 Celery Worker 日志

### 问题 4：智能体模拟器仍提示未配置

**原因：** 浏览器缓存问题

**解决：**
- 刷新页面（Ctrl+F5 或 Cmd+Shift+R）
- 清除浏览器缓存
- 重新打开管理后台

## 相关文档

- [DeepSeek API 配置指南](./DeepSeek_API配置指南.md)
- [消息评分功能故障排查报告](./消息评分功能故障排查报告.md)
- [智能体模拟器双模式说明](./智能体模拟器双模式说明.md)

## 测试脚本

运行测试脚本验证 API 端点：

```bash
python test_api_key_config.py
```

## 技术实现

### 后端实现

**文件：** `api/routes.py`

- `GET /api/admin/config/api-key` - 获取 API Key 状态
- `POST /api/admin/config/api-key` - 更新 API Key

**关键代码：**
```python
@router.get("/admin/config/api-key")
async def admin_get_api_key():
    # 读取 .env 文件
    # 返回掩码后的 API Key
    pass

@router.post("/admin/config/api-key")
async def admin_update_api_key(request: dict):
    # 验证 API Key 格式
    # 更新 .env 文件
    # 更新环境变量
    pass
```

### 前端实现

**文件：** `frontend/admin.html`

**关键组件：**
- 系统配置页面（`config-section`）
- API Key 状态显示
- API Key 输入和保存
- 配置管理对象（`config`）

**关键代码：**
```javascript
const config = {
    async loadApiKeyStatus() {
        // 加载 API Key 状态
    },
    
    async updateApiKey() {
        // 更新 API Key
        // 同步到智能体模拟器
    }
};
```

## 更新日志

### 2024-02-24
- ✅ 新增系统配置页面
- ✅ 实现 API Key 统一配置功能
- ✅ 集成智能体模拟器自动同步
- ✅ 添加 API Key 验证和测试功能
- ✅ 更新相关文档

## 总结

通过管理后台的统一配置功能，管理员可以：

1. 在一个地方配置 API Key
2. 自动应用到所有系统功能
3. 实时查看配置状态
4. 方便地测试和验证

这大大简化了系统配置流程，提升了用户体验。
