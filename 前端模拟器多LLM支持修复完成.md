# 前端模拟器多 LLM 支持修复完成

## 问题描述

用户配置了两个智能体，分别调用 DeepSeek 和 MiniMax，但是日志报错：

```
[18:27:45] ⚠️ MINIMAX 调用失败，使用模板模式: Failed to fetch
[18:27:45] ⚠️ DEEPSEEK 调用失败，使用模板模式: DEEPSEEK API调用失败: 401 Authentication Fails, Your api key: ****1KaM is invalid
```

## 根本原因

`/api/admin/config/llm` 端点之前只返回一个 provider 的配置，无法同时支持两种 LLM。前端 `getLLMConfig()` 方法检查 `config.provider` 和 `config.is_configured`，但当系统配置的默认 provider 是 DeepSeek 时，MiniMax 的配置无法获取；反之亦然。

## 解决方案

### 1. 修改后端 API 端点 (`api/routes.py`)

修改 `get_llm_config` 端点，返回所有 LLM 配置：

```python
@router.get("/admin/config/llm")
async def get_llm_config(db: Session = Depends(get_db)):
    """
    Admin endpoint: Get LLM configuration for simulators.
    Returns all available LLM provider settings from system configuration.
    """
    from services.system_config_service import SystemConfigService

    config_service = SystemConfigService(db)

    # Get LLM provider for scoring (use as default)
    provider = config_service.get_config_value('llm_provider_scoring', 'deepseek')

    # Get API keys for both providers
    deepseek_key = config_service.get_config_value('deepseek_api_key', '')
    minimax_key = config_service.get_config_value('minimax_api_key', '')

    # Mask API keys for security
    def mask_key(key):
        if key and len(key) > 12:
            return key[:8] + "..." + key[-4:]
        elif key:
            return key[:4] + "..."
        return ""

    return {
        "provider": provider,  # Default provider
        "deepseek": {
            "api_key": deepseek_key,
            "masked_key": mask_key(deepseek_key),
            "api_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "is_configured": bool(deepseek_key)
        },
        "minimax": {
            "api_key": minimax_key,
            "masked_key": mask_key(minimax_key),
            "api_url": "https://api.minimax.chat/v1",
            "model": "abab6.5-chat",
            "is_configured": bool(minimax_key)
        },
        # 保留旧格式以兼容
        "api_key": deepseek_key if provider == 'deepseek' else minimax_key,
        "masked_key": mask_key(deepseek_key if provider == 'deepseek' else minimax_key),
        "api_url": "https://api.deepseek.com/v1" if provider == 'deepseek' else "https://api.minimax.chat/v1",
        "model": "deepseek-chat" if provider == 'deepseek' else "abab6.5-chat",
        "is_configured": bool(deepseek_key if provider == 'deepseek' else minimax_key)
    }
```

### 2. 修改前端 `getLLMConfig()` 方法 (`frontend/admin.html`)

适配新的 API 响应格式：

```javascript
async getLLMConfig(mode) {
    try {
        // 从系统配置获取 LLM 配置
        const response = await fetch('/api/admin/config/llm');
        if (!response.ok) {
            throw new Error('获取系统配置失败');
        }
        
        const config = await response.json();
        
        // 根据模式返回相应的配置
        if (mode === 'deepseek') {
            // 使用新的 API 响应格式
            if (config.deepseek && config.deepseek.is_configured) {
                return {
                    api_key: config.deepseek.api_key,
                    api_url: config.deepseek.api_url,
                    model: config.deepseek.model
                };
            }
            // 如果系统配置未设置，尝试使用本地存储的 API Key
            const localKey = this.deepseekApiKey || localStorage.getItem('deepseek_api_key');
            if (localKey) {
                return {
                    api_key: localKey,
                    api_url: 'https://api.deepseek.com/v1',
                    model: 'deepseek-chat'
                };
            }
        } else if (mode === 'minimax') {
            // 使用新的 API 响应格式
            if (config.minimax && config.minimax.is_configured) {
                return {
                    api_key: config.minimax.api_key,
                    api_url: config.minimax.api_url,
                    model: config.minimax.model
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

### 3. 更新 API 文档

更新了以下文档以反映新的 API 响应格式：

- `API_ENDPOINTS.md` - 第 8.5 节
- `static/api-docs.html` - LLM 配置端点

## 新的 API 响应格式

```json
{
  "provider": "deepseek",
  "deepseek": {
    "api_key": "sk-xxxxxxxxxxxxxxxx",
    "masked_key": "sk-xxxxx...xxxx",
    "api_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "is_configured": true
  },
  "minimax": {
    "api_key": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "masked_key": "eyJhbGci...1KaM",
    "api_url": "https://api.minimax.chat/v1",
    "model": "abab6.5-chat",
    "is_configured": true
  },
  "api_key": "sk-xxxxxxxxxxxxxxxx",
  "masked_key": "sk-xxxxx...xxxx",
  "api_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "is_configured": true
}
```

## 优势

1. **同时支持多种 LLM**：一个 API 调用返回所有 LLM 配置
2. **向后兼容**：保留旧格式字段（`api_key`, `masked_key` 等）
3. **灵活选择**：不同智能体可以选择不同的 LLM
4. **统一配置源**：所有配置来自系统配置，无需在多处维护

## 测试步骤

1. 在系统配置中设置 DeepSeek 和 MiniMax 的 API Key
2. 在前端模拟器中添加两个智能体：
   - 智能体 1：发言模式选择 "DeepSeek 调用"
   - 智能体 2：发言模式选择 "MiniMax 调用"
3. 启动两个智能体
4. 观察日志，应该看到：
   - DeepSeek 智能体成功调用 DeepSeek API
   - MiniMax 智能体成功调用 MiniMax API
   - 没有 401 或 Failed to fetch 错误

## 修改的文件

1. `api/routes.py` - 修改 `get_llm_config` 端点
2. `frontend/admin.html` - 修改 `getLLMConfig()` 方法
3. `API_ENDPOINTS.md` - 更新 API 文档
4. `static/api-docs.html` - 更新静态 API 文档

## 注意事项

- 无需重启 Worker，前端刷新页面即可生效
- 确保在系统配置中设置了两种 LLM 的 API Key
- 如果只配置了一种 LLM，另一种会返回 `is_configured: false`
