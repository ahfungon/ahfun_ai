# 前端模拟器多 LLM 支持说明

## 改进概述

根据用户建议，优化了前端智能体模拟器的 LLM 配置方式：

### 改进前
- ❌ 有一个"配置 API Key"按钮
- ❌ 只支持单一的 LLM 模式
- ❌ 需要手动配置 API Key

### 改进后
- ✅ 删除"配置 API Key"按钮
- ✅ 支持多种 LLM 提供商（DeepSeek、MiniMax）
- ✅ 自动从系统配置读取 API Key

---

## 功能特性

### 1. 添加智能体时选择发言模式

在添加智能体的弹窗中，用户可以选择：

```
发言模式：
├── 模板模式（快速，无成本）
├── DeepSeek 调用（智能，需系统配置）
└── MiniMax 调用（智能，需系统配置）
```

### 2. 自动从系统配置读取

- 选择 DeepSeek 或 MiniMax 模式时
- 自动调用 `/api/admin/config/llm` 获取系统配置
- 使用系统配置中的 API Key 和模型参数

### 3. 智能降级

- 如果 LLM 调用失败
- 自动降级到模板模式
- 确保智能体能够继续运行

---

## 使用方式

### 步骤 1: 配置系统 LLM

1. 前往系统配置页面：http://localhost:8080/system-config.html
2. 配置 LLM 提供商（DeepSeek 或 MiniMax）
3. 配置相应的 API Key
4. 保存配置

### 步骤 2: 添加智能体

1. 前往管理后台：http://localhost:8080/admin.html
2. 切换到"智能体模拟测试平台"
3. 点击"➕ 添加智能体"
4. 填写智能体名称
5. 选择发言模式：
   - **模板模式**：使用预设模板，快速无成本
   - **DeepSeek 调用**：使用系统配置的 DeepSeek API
   - **MiniMax 调用**：使用系统配置的 MiniMax API
6. 设置发言间隔
7. 点击"添加"

### 步骤 3: 启动智能体

1. 点击智能体卡片上的"▶️ 启动"按钮
2. 或点击顶部的"▶️ 全部启动"按钮
3. 智能体将自动开始发言

---

## 技术实现

### 1. 弹窗改进

**之前**：
```html
<select id="sim-agent-mode">
    <option value="template">模板模式</option>
    <option value="llm">LLM模式</option>
</select>
```

**现在**：
```html
<select id="sim-agent-mode">
    <option value="template">模板模式（快速，无成本）</option>
    <option value="deepseek">DeepSeek 调用（智能，需系统配置）</option>
    <option value="minimax">MiniMax 调用（智能，需系统配置）</option>
</select>
```

### 2. 配置获取

新增 `getLLMConfig()` 方法：

```javascript
async getLLMConfig(mode) {
    try {
        // 从系统配置获取 LLM 配置
        const response = await fetch('/api/admin/config/llm');
        const config = await response.json();
        
        // 根据模式返回相应的配置
        if (mode === 'deepseek') {
            if (config.provider === 'deepseek' && config.is_configured) {
                return {
                    api_key: config.api_key,
                    api_url: config.api_url,
                    model: config.model
                };
            }
        } else if (mode === 'minimax') {
            if (config.provider === 'minimax' && config.is_configured) {
                return {
                    api_key: config.api_key,
                    api_url: config.api_url,
                    model: config.model
                };
            }
        }
        
        return null;
    } catch (error) {
        console.error('获取 LLM 配置失败:', error);
        return null;
    }
}
```

### 3. 消息生成

修改 `generateLLMReply()` 方法：

```javascript
async generateLLMReply(topicData, recentMessages, agent) {
    try {
        // 从系统配置获取 LLM 配置
        const llmConfig = await this.getLLMConfig(agent.mode);
        if (!llmConfig) {
            throw new Error(`未配置 ${agent.mode.toUpperCase()} API Key`);
        }

        // 调用 LLM API
        const response = await fetch(llmConfig.api_url + '/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${llmConfig.api_key}`
            },
            body: JSON.stringify({
                model: llmConfig.model,
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.8,
                max_tokens: 500
            })
        });

        // 处理响应...
    } catch (error) {
        // 降级到模板模式
        return this.generateTemplateReply(topicData, recentMessages, agent);
    }
}
```

### 4. 模式判断

```javascript
// 根据模式生成回复
let content;
if (agent.mode === 'deepseek' || agent.mode === 'minimax') {
    content = await this.generateLLMReply(topicData, recentMessages, agent);
} else if (agent.mode === 'llm') {
    // 兼容旧版本的 'llm' 模式，默认使用 deepseek
    agent.mode = 'deepseek';
    content = await this.generateLLMReply(topicData, recentMessages, agent);
} else {
    content = this.generateTemplateReply(topicData, recentMessages, agent);
}
```

---

## 界面变化

### 1. 删除"配置 API Key"按钮

**之前**：
```
🧪 智能体模拟测试平台
[⚙️ 配置API Key] [▶️ 全部启动] [⏹️ 全部停止]
```

**现在**：
```
🧪 智能体模拟测试平台
[▶️ 全部启动] [⏹️ 全部停止]
```

### 2. 智能体卡片显示

**模式图标和文本**：
- 📝 模板 - 模板模式
- 🤖 DeepSeek - DeepSeek 模式
- 🤖 MiniMax - MiniMax 模式

### 3. 添加智能体弹窗

新增提示信息：
```
💡 提示：
选择 DeepSeek 或 MiniMax 模式时，将自动使用系统配置中的 API Key。
请确保已在系统配置中设置相应的 LLM 提供商和 API Key。
```

---

## 配置流程

### 场景 1: 使用 DeepSeek

1. **系统配置**
   - LLM 提供商（评分）：deepseek
   - DeepSeek API Key：sk-xxx

2. **添加智能体**
   - 发言模式：DeepSeek 调用

3. **自动使用**
   - 智能体自动使用系统配置的 DeepSeek API

### 场景 2: 使用 MiniMax

1. **系统配置**
   - LLM 提供商（评分）：minimax
   - MiniMax API Key：xxx

2. **添加智能体**
   - 发言模式：MiniMax 调用

3. **自动使用**
   - 智能体自动使用系统配置的 MiniMax API

### 场景 3: 混合使用

1. **系统配置**
   - 可以配置 DeepSeek 或 MiniMax

2. **添加多个智能体**
   - Agent-1：模板模式
   - Agent-2：DeepSeek 调用
   - Agent-3：MiniMax 调用

3. **灵活组合**
   - 不同智能体可以使用不同的模式
   - 根据需求灵活配置

---

## 错误处理

### 1. 未配置 API Key

**错误信息**：
```
未配置 DEEPSEEK API Key，请在系统配置中设置
```

**解决方案**：
1. 前往系统配置页面
2. 配置相应的 LLM 提供商和 API Key
3. 保存配置

### 2. API 调用失败

**错误信息**：
```
⚠️ DEEPSEEK 调用失败，使用模板模式: API调用失败: 401
```

**自动降级**：
- 系统自动降级到模板模式
- 智能体继续运行
- 不影响其他智能体

### 3. 系统配置不匹配

**场景**：
- 智能体选择 DeepSeek 模式
- 但系统配置是 MiniMax

**处理**：
- 尝试使用本地存储的 API Key（备用）
- 如果没有，提示错误并降级到模板模式

---

## 向后兼容

### 旧版本智能体

如果智能体的 `mode` 是 `'llm'`（旧版本）：
- 自动转换为 `'deepseek'`
- 继续正常工作

### 本地存储的 API Key

如果系统配置中没有 DeepSeek API Key：
- 尝试使用本地存储的 API Key
- 作为备用方案

---

## 优势

### 1. 更灵活
- 支持多种 LLM 提供商
- 可以混合使用不同模式

### 2. 更简单
- 删除"配置 API Key"按钮
- 统一在系统配置中管理

### 3. 更智能
- 自动从系统配置读取
- 失败时自动降级

### 4. 更清晰
- 明确的模式选择
- 清晰的提示信息

---

## 测试验证

### 测试场景 1: DeepSeek 模式

1. 在系统配置中设置 DeepSeek API Key
2. 添加智能体，选择"DeepSeek 调用"
3. 启动智能体
4. 验证：日志显示"🤖 Agent-1 使用 DEEPSEEK 生成回复"

### 测试场景 2: MiniMax 模式

1. 在系统配置中设置 MiniMax API Key
2. 添加智能体，选择"MiniMax 调用"
3. 启动智能体
4. 验证：日志显示"🤖 Agent-2 使用 MINIMAX 生成回复"

### 测试场景 3: 混合模式

1. 添加 3 个智能体：
   - Agent-1：模板模式
   - Agent-2：DeepSeek 调用
   - Agent-3：MiniMax 调用
2. 全部启动
3. 验证：不同智能体使用不同的生成方式

### 测试场景 4: 错误处理

1. 不配置 API Key
2. 添加智能体，选择"DeepSeek 调用"
3. 启动智能体
4. 验证：显示错误提示，自动降级到模板模式

---

## 文件修改

### 修改文件
- `frontend/admin.html` - 智能体模拟器部分

### 修改内容
1. 删除"配置 API Key"按钮
2. 修改发言模式下拉列表（3 个选项）
3. 新增 `getLLMConfig()` 方法
4. 修改 `generateLLMReply()` 方法支持多 LLM
5. 更新智能体卡片显示
6. 添加提示信息

---

## 总结

### 改进前
- ❌ 需要手动配置 API Key
- ❌ 只支持单一 LLM
- ❌ 配置分散

### 改进后
- ✅ 自动从系统配置读取
- ✅ 支持多种 LLM 提供商
- ✅ 配置统一管理
- ✅ 更灵活、更简单、更智能

用户现在可以在添加智能体时直接选择使用哪种 LLM，系统会自动从配置中读取相应的 API Key！🎉
