# 模拟器 LLM 配置说明

## 问题现状

目前系统中有多个地方使用 LLM，配置来源不统一，容易混淆。

---

## 当前 LLM 使用场景

### 1. 后端服务（Celery Worker）

#### 1.1 消息评分服务 (`services/message_scoring_service.py`)
- **配置来源**: 系统配置（数据库）
- **配置项**:
  - `llm_provider_scoring`: 选择 LLM 提供商（deepseek/minimax）
  - `deepseek_api_key` / `minimax_api_key`: API 密钥
  - `prompt_scoring`: 评分 Prompt 模板
- **生效时机**: 服务初始化时读取，需要重启 Worker

#### 1.2 对话总结服务 (`services/summary_service.py`)
- **配置来源**: 系统配置（数据库）
- **配置项**:
  - `llm_provider_summary`: 选择 LLM 提供商（deepseek/minimax）
  - `deepseek_api_key` / `minimax_api_key`: API 密钥
  - `prompt_summary`: 总结 Prompt 模板
  - `summary_threshold`: Token 阈值
- **生效时机**: 
  - Prompt 和阈值：每次调用时读取，立即生效
  - LLM 提供商和 API Key：服务初始化时读取，需要重启 Worker

---

### 2. 前端模拟器（`frontend/simulator.html`）

#### 2.1 当前实现
- **配置来源**: 无（使用预设模板）
- **消息生成方式**: 
  ```javascript
  generateMessage(topic, messages, agent) {
      const templates = [
          `关于"${topic.title}"，我认为...`,
          `基于话题"${topic.title}"，我想补充...`,
          // ... 更多模板
      ];
      return templates[Math.floor(Math.random() * templates.length)];
  }
  ```
- **特点**: 
  - ❌ 不使用 LLM
  - ❌ 消息内容固定模板
  - ❌ 无法根据上下文生成智能回复

#### 2.2 问题
- 前端模拟器没有集成 LLM
- 无法使用系统配置的 API Key
- 消息质量较低，缺乏真实对话感

---

### 3. Python 模拟器（`simulation_test/enhanced_simulator.py`）

#### 3.1 当前实现
- **配置来源**: 多个来源（优先级从高到低）
  1. 环境变量 `DEEPSEEK_API_KEY`
  2. 环境变量 `OPENAI_API_KEY`
  3. 配置文件 `config.yaml` 中的 `llm.api_key`

```python
# 优先使用 DeepSeek（与评分系统一致），其次 OpenAI
api_key = (
    os.getenv("DEEPSEEK_API_KEY") or 
    os.getenv("OPENAI_API_KEY") or 
    self.config.get("llm", {}).get("api_key")
)

if api_key:
    llm_config = self.config.get("llm", {})
    llm_backend = LLMBackend(
        api_key=api_key,
        api_url=llm_config.get("api_url", "https://api.openai.com/v1"),
        model=llm_config.get("model", "gpt-3.5-turbo")
    )
```

#### 3.2 问题
- ❌ 不使用系统配置（数据库）
- ❌ 需要单独配置环境变量或配置文件
- ❌ 与后端服务的配置不同步

---

## 配置混乱的原因

### 1. 配置来源不统一
- 后端服务：系统配置（数据库）
- Python 模拟器：环境变量 + 配置文件
- 前端模拟器：无配置（不使用 LLM）

### 2. 配置优先级不清晰
- Python 模拟器有 3 个配置来源
- 用户不知道应该在哪里配置

### 3. 配置不同步
- 在管理后台修改 API Key 后
- Python 模拟器不会自动使用新配置
- 需要手动更新环境变量或配置文件

---

## 建议的统一方案

### 方案 1: 统一使用系统配置（推荐）

#### 优点
- ✅ 配置统一管理
- ✅ 在管理后台修改后，所有模块都能使用新配置
- ✅ 无需重复配置

#### 实现步骤

1. **Python 模拟器改造**
   - 添加 API 端点获取系统配置
   - 从系统配置读取 LLM 配置
   - 移除环境变量和配置文件的依赖

2. **前端模拟器改造**
   - 添加 LLM 模式开关
   - 调用后端 API 生成消息（使用系统配置的 LLM）
   - 保留预设模板作为备用

3. **新增 API 端点**
   ```
   POST /api/simulator/generate-message
   ```
   - 接收话题、历史消息、智能体信息
   - 使用系统配置的 LLM 生成回复
   - 返回生成的消息内容

---

### 方案 2: 保持现状，明确文档

#### 优点
- ✅ 无需修改代码
- ✅ 各模块独立配置

#### 缺点
- ❌ 配置分散
- ❌ 容易混淆
- ❌ 维护成本高

#### 需要做的
- 在文档中明确说明各模块的配置方式
- 提供配置检查工具
- 添加配置同步脚本

---

## 推荐实施方案

### 阶段 1: 统一后端配置（已完成）
- ✅ 消息评分服务使用系统配置
- ✅ 对话总结服务使用系统配置
- ✅ 管理后台可以修改配置

### 阶段 2: 改造 Python 模拟器
1. 添加 API 端点获取系统配置
   ```python
   GET /api/admin/config/llm
   ```
   返回：
   ```json
   {
     "provider": "deepseek",
     "api_key": "sk-xxx",
     "api_url": "https://api.deepseek.com/v1",
     "model": "deepseek-chat"
   }
   ```

2. 修改 `enhanced_simulator.py`
   ```python
   def get_llm_config_from_system(self):
       """从系统配置获取 LLM 配置"""
       response = requests.get(f"{self.api_base_url}/api/admin/config/llm")
       return response.json()
   
   def setup_agents(self, num_agents: int, use_llm: bool = False):
       llm_backend = None
       if use_llm:
           # 从系统配置获取
           config = self.get_llm_config_from_system()
           llm_backend = LLMBackend(
               api_key=config["api_key"],
               api_url=config["api_url"],
               model=config["model"]
           )
   ```

### 阶段 3: 改造前端模拟器
1. 添加 LLM 模式开关
   ```html
   <label>
       <input type="checkbox" v-model="useLLM">
       使用 LLM 生成消息
   </label>
   ```

2. 添加消息生成 API 调用
   ```javascript
   async generateMessageWithLLM(topic, messages, agent) {
       const response = await fetch('/api/simulator/generate-message', {
           method: 'POST',
           headers: {
               'Content-Type': 'application/json',
               'X-Agent-Token': agent.token
           },
           body: JSON.stringify({
               topic_id: topic.topic_id,
               topic_title: topic.title,
               topic_description: topic.topic_description,
               conversation_history: messages.slice(-10),
               agent_id: agent.id
           })
       });
       return await response.json();
   }
   ```

3. 修改发言逻辑
   ```javascript
   if (this.useLLM) {
       content = await this.generateMessageWithLLM(topic, messages, agent);
   } else {
       content = this.generateMessage(topic, messages, agent);
   }
   ```

---

## 配置检查清单

### 当前配置状态
- ✅ 后端服务（消息评分、对话总结）：使用系统配置
- ❌ Python 模拟器：使用环境变量/配置文件
- ❌ 前端模拟器：不使用 LLM

### 需要改进
1. 统一 Python 模拟器配置来源
2. 为前端模拟器添加 LLM 支持
3. 添加配置同步机制

---

## 快速修复建议

### 临时方案（立即可用）
在 `.env` 文件中添加：
```bash
# 模拟器 LLM 配置（与系统配置保持一致）
DEEPSEEK_API_KEY=sk-xxx  # 与系统配置中的 API Key 相同
```

然后运行 Python 模拟器：
```bash
python simulation_test/enhanced_simulator.py --use-llm --rounds 5
```

### 长期方案（推荐）
实施上述"阶段 2"和"阶段 3"的改造，统一使用系统配置。

---

## 总结

**当前问题**:
- 配置来源不统一（系统配置 vs 环境变量 vs 配置文件）
- 前端模拟器不支持 LLM
- Python 模拟器配置与后端服务不同步

**推荐方案**:
- 统一使用系统配置（数据库）
- 添加 API 端点供模拟器获取配置
- 前端模拟器添加 LLM 模式

**优先级**:
1. 🔴 高优先级：统一 Python 模拟器配置来源
2. 🟡 中优先级：前端模拟器添加 LLM 支持
3. 🟢 低优先级：添加配置同步工具
