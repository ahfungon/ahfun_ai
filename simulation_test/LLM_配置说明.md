# 模拟器 LLM 配置说明

## 概述

增强版模拟器支持使用真实 LLM 生成对话内容。系统中有两个地方使用 LLM：

### 1. 评分系统（后端）✅ 已配置

**位置**: `services/message_scoring_service.py`

**用途**: 评估每条消息与话题的相关性

**使用的 LLM**: DeepSeek API

**配置位置**: `.env` 文件

```bash
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_URL=https://api.deepseek.com/v1
```

**状态**: ✅ 已经在使用，每条消息发送后自动评分

---

### 2. 对话生成（模拟器）⚙️ 可选配置

**位置**: `simulation_test/enhanced_simulator.py`

**用途**: 模拟智能体生成对话内容

**支持的 LLM**: DeepSeek（推荐）或 OpenAI

**配置位置**: 
- 环境变量（推荐）
- `simulation_test/config.yaml`

**状态**: ⚙️ 可选功能，使用 `--use-llm` 参数启用

---

## 配置方法

### 方法 1: 使用环境变量（推荐）

#### 使用 DeepSeek（推荐，与评分系统一致）

```bash
# 设置 DeepSeek API 密钥
export DEEPSEEK_API_KEY="your-deepseek-api-key"

# 运行模拟器
cd simulation_test
python enhanced_simulator.py --use-llm
```

#### 使用 OpenAI（备选）

```bash
# 设置 OpenAI API 密钥
export OPENAI_API_KEY="your-openai-api-key"

# 运行模拟器
cd simulation_test
python enhanced_simulator.py --use-llm
```

### 方法 2: 修改配置文件

编辑 `simulation_test/config.yaml`：

```yaml
llm:
  # DeepSeek 配置（推荐）
  api_key: "your-deepseek-api-key"
  api_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"
```

---

## API 密钥优先级

模拟器按以下顺序查找 API 密钥：

1. **环境变量 `DEEPSEEK_API_KEY`** ← 最高优先级
2. 环境变量 `OPENAI_API_KEY`
3. `config.yaml` 中的 `llm.api_key`

**推荐**: 使用环境变量 `DEEPSEEK_API_KEY`，这样：
- ✅ 与评分系统使用同一个 API
- ✅ 不需要在配置文件中暴露密钥
- ✅ 便于在不同环境切换

---

## 使用场景

### 场景 1: 不使用 LLM（默认）

```bash
python enhanced_simulator.py
```

- 使用预设的对话内容
- 不需要 API 密钥
- 适合快速功能测试

### 场景 2: 使用 DeepSeek 生成对话

```bash
# 从 .env 文件读取（如果已配置）
source ../.env
export DEEPSEEK_API_KEY

# 或直接设置
export DEEPSEEK_API_KEY="your-key"

# 运行
python enhanced_simulator.py --use-llm
```

- 使用真实 LLM 生成对话
- 对话质量更高、更自然
- 适合测试评分系统

### 场景 3: 使用 OpenAI 生成对话

```bash
export OPENAI_API_KEY="your-openai-key"
python enhanced_simulator.py --use-llm
```

- 使用 OpenAI API
- 需要单独的 API 密钥
- 备选方案

---

## 完整配置示例

### 1. 检查现有配置

```bash
# 查看 .env 文件
cat .env | grep DEEPSEEK

# 应该看到：
# DEEPSEEK_API_KEY=sk-xxxxx
# DEEPSEEK_API_URL=https://api.deepseek.com/v1
```

### 2. 设置环境变量

```bash
# 加载 .env 文件
source .env

# 或手动设置
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

### 3. 验证配置

```bash
# 检查环境变量
echo $DEEPSEEK_API_KEY

# 应该输出你的 API 密钥
```

### 4. 运行模拟器

```bash
cd simulation_test

# 使用 LLM 生成对话
python enhanced_simulator.py --use-llm --rounds 5

# 或使用 Makefile
make test-llm
```

---

## 两个 LLM 的区别

| 特性 | 评分系统 LLM | 模拟器 LLM |
|------|-------------|-----------|
| **位置** | 后端服务 | 测试脚本 |
| **用途** | 评估消息相关性 | 生成对话内容 |
| **触发** | 自动（每条消息） | 手动（--use-llm） |
| **必需** | ✅ 是 | ❌ 否（可选） |
| **配置** | .env 文件 | 环境变量或 config.yaml |
| **API** | DeepSeek | DeepSeek 或 OpenAI |

---

## 推荐配置

### 开发环境

```bash
# .env 文件（已有）
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_URL=https://api.deepseek.com/v1

# 使用同一个 API 密钥
export DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY .env | cut -d '=' -f2)

# 运行模拟器
cd simulation_test
python enhanced_simulator.py --use-llm
```

### 生产环境

```bash
# 只需要配置评分系统的 DeepSeek
# 模拟器通常不在生产环境运行
```

---

## 成本考虑

### 评分系统（后端）

- **每条消息**: 1 次 API 调用
- **Token 消耗**: ~500-1000 tokens/次
- **成本**: 根据 DeepSeek 定价

### 模拟器（测试）

- **每条消息**: 1 次 API 调用
- **Token 消耗**: ~300-500 tokens/次
- **成本**: 仅在测试时产生

**建议**: 
- 评分系统必须使用 LLM（核心功能）
- 模拟器可以不使用 LLM（节省成本）
- 只在需要测试评分系统时才启用 `--use-llm`

---

## 故障排除

### 问题 1: API 密钥未找到

**错误**: `未找到 LLM API 密钥，将使用预设回复`

**解决**:
```bash
# 检查环境变量
echo $DEEPSEEK_API_KEY

# 如果为空，设置它
export DEEPSEEK_API_KEY="your-key"
```

### 问题 2: API 调用失败

**错误**: `LLM 生成失败: ...`

**解决**:
1. 检查 API 密钥是否正确
2. 检查网络连接
3. 检查 API 配额
4. 查看详细错误日志

### 问题 3: 使用了错误的 API

**症状**: 想用 DeepSeek 但调用了 OpenAI

**解决**:
```bash
# 确保 DEEPSEEK_API_KEY 已设置
export DEEPSEEK_API_KEY="your-deepseek-key"

# 取消 OPENAI_API_KEY（如果设置了）
unset OPENAI_API_KEY

# 或者修改 config.yaml
```

---

## 验证配置

运行以下命令验证配置是否正确：

```bash
cd simulation_test

# 测试不使用 LLM（应该成功）
python enhanced_simulator.py --rounds 2

# 测试使用 LLM（需要 API 密钥）
export DEEPSEEK_API_KEY="your-key"
python enhanced_simulator.py --use-llm --rounds 2
```

如果看到类似输出，说明配置成功：

```
✓ LLM 后端已启用

[10:30:15] Agent-1:
  我认为人工智能在医疗影像诊断方面有巨大潜力...
  (Tokens: 156, 累计: 156)
```

---

## 总结

- ✅ **评分系统**: 已经在使用 DeepSeek，配置在 `.env`
- ⚙️ **模拟器**: 可选使用 LLM，推荐使用 DeepSeek
- 💡 **推荐**: 使用环境变量 `DEEPSEEK_API_KEY`
- 💰 **成本**: 模拟器可以不用 LLM 来节省成本

## 快速命令

```bash
# 使用 DeepSeek 运行模拟器
export DEEPSEEK_API_KEY="your-key"
cd simulation_test
python enhanced_simulator.py --use-llm --rounds 5
```
