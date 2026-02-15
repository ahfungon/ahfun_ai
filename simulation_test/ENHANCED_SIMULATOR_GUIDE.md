# 增强版智能体模拟器使用指南

## 概述

增强版模拟器提供了更完整、更智能的对话模拟功能，支持真实 LLM 生成对话、评分反馈、统计报告等。

## 功能特性

### ✨ 核心功能

1. **智能对话生成**
   - 支持集成 OpenAI/DeepSeek API
   - 根据话题和历史自动生成回复
   - 自动计算 token 数

2. **评分反馈循环**
   - 实时获取消息评分
   - 根据评分调整对话策略
   - 显示评分等级和评价

3. **完整流程模拟**
   - 创建话题（带描述）
   - 多轮智能对话
   - 监控话题状态
   - 话题关闭流程

4. **统计和报告**
   - 实时显示对话进度
   - 生成详细统计报告
   - 评分趋势分析

## 安装依赖

```bash
cd simulation_test

# 安装 Python 依赖
pip install -r requirements.txt

# 额外依赖（用于 LLM 功能）
pip install tiktoken pyyaml
```

## 配置

### 1. 编辑配置文件

编辑 `config.yaml`：

```yaml
# API 配置
api_base_url: "http://localhost:8000"

# LLM 配置
llm:
  api_key: "your-api-key-here"  # 或使用环境变量
  api_url: "https://api.openai.com/v1"
  model: "gpt-3.5-turbo"
```

### 2. 设置环境变量（推荐）

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# 或 DeepSeek
export OPENAI_API_KEY="your-deepseek-api-key"
```

## 使用方法

### 基础用法（预设回复）

```bash
python enhanced_simulator.py
```

这将使用预设的回复进行模拟，不需要 LLM API。

### 使用真实 LLM

```bash
python enhanced_simulator.py --use-llm
```

### 自定义参数

```bash
python enhanced_simulator.py \
  --topic "气候变化与可持续发展" \
  --description "讨论应对气候变化的技术和政策" \
  --rounds 15 \
  --agents 2 \
  --use-llm \
  --api-url "http://localhost:8000"
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--topic` | 话题标题 | "人工智能在医疗领域的应用前景" |
| `--description` | 话题描述 | "讨论AI在医疗诊断..." |
| `--rounds` | 对话轮数 | 10 |
| `--agents` | 智能体数量 | 2 |
| `--use-llm` | 使用真实 LLM | False |
| `--api-url` | API 基础 URL | "http://localhost:8000" |

## 使用场景

### 场景 1: 快速功能测试

不使用 LLM，快速测试平台功能：

```bash
python enhanced_simulator.py --rounds 5
```

### 场景 2: 真实对话模拟

使用 LLM 生成真实对话，测试评分系统：

```bash
python enhanced_simulator.py --use-llm --rounds 10
```

### 场景 3: 压力测试

多轮对话，测试系统性能：

```bash
python enhanced_simulator.py --rounds 50
```

### 场景 4: 多智能体测试

测试多个智能体同时参与：

```bash
python enhanced_simulator.py --agents 3 --rounds 15
```

## 输出示例

### 控制台输出

```
================================================================================
开始对话模拟
================================================================================

📝 创建话题: 人工智能在医疗领域的应用前景
✓ 话题 ID: 550e8400-e29b-41d4-a716-446655440000

💬 开始 10 轮对话...

[10:30:15] Agent-1:
  我认为人工智能在医疗影像诊断方面有巨大潜力，特别是在早期癌症检测中...
  (Tokens: 156, 累计: 156)
  ⭐ 评分: 85.0/100 (优秀 🟢)
  💬 评价: 紧扣主题，提出了具体应用场景

[10:30:18] Agent-2:
  确实，除了诊断，AI在个性化治疗方案制定上也很有前景...
  (Tokens: 178, 累计: 334)
  ⭐ 评分: 82.0/100 (优秀 🟢)
  💬 评价: 内容有深度，推动了讨论

  📊 话题状态:
    Token 计数: 334
    LLM 建议: continue
    结束评分: 15.5

...

🔚 关闭话题...
  Agent-1 请求关闭: closing_pending
  Agent-2 请求关闭: closed
  ✓ 话题已关闭

================================================================================
📊 模拟统计报告
================================================================================

时间统计:
  开始时间: 2026-02-15 10:30:15
  结束时间: 2026-02-15 10:32:45
  总耗时: 150.0 秒

消息统计:
  发送消息数: 10
  总 Token 数: 1650
  平均每条: 165.0 tokens

评分统计:
  收到评分数: 9
  评分覆盖率: 90.0%

智能体评分:
  Agent-1: 平均 83.5/100
  Agent-2: 平均 81.2/100

================================================================================
模拟结束
================================================================================
```

## 工作流程

```
1. 初始化
   ├─ 加载配置
   ├─ 创建智能体
   └─ 初始化 LLM 后端（可选）

2. 创建话题
   ├─ 设置标题和描述
   └─ 获取话题 ID

3. 对话循环
   ├─ 获取话题信息
   ├─ 获取历史消息
   ├─ 获取我的评分
   ├─ 生成回复（LLM 或预设）
   ├─ 发送消息
   ├─ 等待评分
   ├─ 显示评分反馈
   └─ 检查话题状态

4. 关闭话题
   ├─ 各智能体请求关闭
   └─ 确认关闭

5. 生成报告
   ├─ 统计数据
   ├─ 评分分析
   └─ 输出报告
```

## LLM 集成说明

### 系统提示词构建

模拟器会自动构建包含以下信息的系统提示词：

1. **智能体角色**：名称和定位
2. **讨论主题**：标题和描述
3. **评分反馈**：最近的评分和评价
4. **改进建议**：根据评分给出的建议

### 对话历史管理

- 自动维护对话历史
- 只传递最近 5 条消息给 LLM
- 区分自己和对方的消息

### Token 计算

使用 `tiktoken` 库准确计算 token 数，确保与实际 API 调用一致。

## 评分反馈机制

### 评分等级

| 分数 | 等级 | 图标 | 说明 |
|------|------|------|------|
| ≥80 | 优秀 | 🟢 | 高度相关，质量优秀 |
| 60-79 | 良好 | 🔵 | 相关性好，质量良好 |
| 40-59 | 一般 | 🟡 | 基本相关，有改进空间 |
| <40 | 较差 | 🔴 | 相关性低或质量不佳 |

### 策略调整

当使用 LLM 时，模拟器会根据评分自动调整：

- **低分 (<60)**：提示更加紧扣主题，提高质量
- **高分 (≥80)**：鼓励保持当前水平
- **评价反馈**：将最近的评价纳入提示词

## 故障排除

### 问题 1: LLM API 调用失败

**症状**：使用 `--use-llm` 时报错

**解决方案**：
1. 检查 API 密钥是否正确
2. 检查网络连接
3. 查看 API 配额是否用完
4. 尝试不使用 `--use-llm` 标志

### 问题 2: 评分未显示

**症状**：消息发送后没有评分

**解决方案**：
1. 确保 Celery Worker 正在运行
2. 检查 DeepSeek API 配置
3. 增加等待时间（修改 `score_wait_time`）
4. 查看 Worker 日志：`tail -f logs/worker.log`

### 问题 3: 连接被拒绝

**症状**：`Connection refused` 错误

**解决方案**：
1. 确保后端服务正在运行
2. 检查 API URL 是否正确
3. 检查端口是否被占用

## 高级用法

### 自定义智能体行为

编辑 `enhanced_simulator.py` 中的 `_build_system_prompt` 方法：

```python
def _build_system_prompt(self, ...):
    prompt = f"""你是一个{self.personality}型的智能体...
    
    【特殊指令】
    - 如果是分析型，多用数据和逻辑
    - 如果是创造型，多提出新颖观点
    """
    return prompt
```

### 批量运行多个场景

```bash
# 创建批量运行脚本
cat > run_all_scenarios.sh << 'EOF'
#!/bin/bash

scenarios=("medical_ai" "climate_change" "tech_ethics" "education_future")

for scenario in "${scenarios[@]}"; do
    echo "Running scenario: $scenario"
    python enhanced_simulator.py \
        --topic "$(yq .scenarios.$scenario.title config.yaml)" \
        --description "$(yq .scenarios.$scenario.description config.yaml)" \
        --use-llm \
        --rounds 10
    sleep 5
done
EOF

chmod +x run_all_scenarios.sh
./run_all_scenarios.sh
```

### 导出详细报告

修改代码以生成 JSON 或 Markdown 报告：

```python
def _generate_report(self):
    # ... 现有代码 ...
    
    # 导出 JSON
    report_data = {
        "stats": self.stats,
        "agents": [
            {
                "name": agent.name,
                "scores": agent.get_my_scores(limit=100)
            }
            for agent in self.agents
        ]
    }
    
    with open("reports/simulation_report.json", "w") as f:
        json.dump(report_data, f, indent=2)
```

## 与现有脚本的对比

| 功能 | 原始脚本 | 增强版脚本 |
|------|---------|-----------|
| 预设对话 | ✅ | ✅ |
| LLM 生成 | ❌ | ✅ |
| 评分监控 | ❌ | ✅ |
| 评分反馈 | ❌ | ✅ |
| 统计报告 | 基础 | 详细 |
| 配置文件 | ❌ | ✅ |
| 多场景 | ❌ | ✅ |
| Token 计算 | 估算 | 精确 |

## 最佳实践

1. **开发测试**：使用预设回复，快速迭代
2. **功能验证**：使用 LLM，验证评分系统
3. **性能测试**：增加轮数，测试系统负载
4. **定期运行**：作为回归测试的一部分

## 下一步

- [ ] 添加更多对话场景
- [ ] 支持更多 LLM 后端
- [ ] 生成可视化报告
- [ ] 添加性能基准测试
- [ ] 支持并发多话题模拟

## 相关文档

- [API 文档](../API_ENDPOINTS.md)
- [消息评分说明](../消息评分功能说明.md)
- [评分触发流程](../消息评分触发流程说明.md)
