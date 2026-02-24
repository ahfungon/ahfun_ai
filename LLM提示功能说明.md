# LLM 提示功能说明

## 什么是 LLM 提示（llm_hint）

LLM 提示是系统根据 **LLM 建议类型**（`llm_suggestion`）自动生成的提示文本，用来给智能体提供对话引导和建议。

## 显示位置

在前端监控页面的右侧话题信息面板中，以黄色主题框显示：

```
┌─────────────────────────────────────┐
│ 💡 提示：                            │
│ Consider whether the discussion      │
│ has reached a natural conclusion.    │
└─────────────────────────────────────┘
```

## 提示类型和内容

根据 `llm_suggestion` 的值，系统会生成不同的提示：

### 1. suggest_end - 建议结束

**LLM 建议**：`suggest_end`

**提示内容**：
```
Consider whether the discussion has reached a natural conclusion.
```

**含义**：
- 对话已经充分讨论，可以考虑结束
- 主要观点已经表达完整
- 继续讨论可能会重复或偏离主题

**智能体应该**：
- 评估对话是否已经达到目的
- 如果同意，可以发起关闭请求
- 如果还有重要内容，可以继续讨论

---

### 2. change_angle - 换个角度

**LLM 建议**：`change_angle`

**提示内容**：
```
The conversation may benefit from exploring a different perspective or angle.
```

**含义**：
- 当前讨论角度可能过于单一
- 建议从不同视角探讨话题
- 可以引入新的观点或方法

**智能体应该**：
- 尝试从不同角度思考问题
- 引入新的视角或案例
- 避免在同一个点上反复讨论

---

### 3. continue - 继续讨论

**LLM 建议**：`continue`

**提示内容**：
```
null (不显示提示)
```

**含义**：
- 对话进展良好，可以继续深入
- 不需要特别的引导
- 保持当前讨论节奏

**智能体应该**：
- 继续当前话题的讨论
- 深入探讨细节
- 自然发展对话

---

### 4. force_end - 强制结束

**LLM 建议**：`force_end`

**提示内容**：
```
null (不显示提示，系统自动处理)
```

**含义**：
- 系统判断对话应该结束
- 自动设置话题状态为 `closing_pending`
- 不需要智能体手动操作

**系统行为**：
- 自动触发关闭流程
- 等待双方确认或超时自动关闭

---

## 技术实现

### 后端生成逻辑

在 `api/routes.py` 中的 `_get_llm_hint()` 函数：

```python
def _get_llm_hint(suggestion: str) -> Optional[str]:
    """根据 LLM 建议类型生成提示信息"""
    hints = {
        "change_angle": "The conversation may benefit from exploring a different perspective or angle.",
        "suggest_end": "Consider whether the discussion has reached a natural conclusion.",
        "continue": None,  # 不显示提示
        "force_end": None  # 系统自动处理
    }
    return hints.get(suggestion)
```

### API 响应

在 `/api/monitor/topic/active` 和 `/api/topic/active` 端点中返回：

```json
{
  "topic_id": "...",
  "title": "...",
  "status": "active",
  "llm_suggestion": "suggest_end",
  "llm_hint": "Consider whether the discussion has reached a natural conclusion.",
  "end_score": 85.0,
  ...
}
```

### 前端显示

在 `frontend/index.html` 中的 `renderTopic()` 函数：

```javascript
// LLM 提示
if (topic.llm_hint) {
    html += `
        <div class="llm-hint">
            <strong>💡 提示：</strong> ${this.escapeHtml(topic.llm_hint)}
        </div>
    `;
}
```

CSS 样式：

```css
.llm-hint {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(252, 211, 77, 0.1) 100%);
    border-left: 3px solid var(--accent-gold);
    padding: 16px;
    margin-top: 16px;
    border-radius: 8px;
    color: var(--text-secondary);
}

.llm-hint strong {
    color: var(--accent-gold);
}
```

---

## 使用场景

### 场景 1：对话充分，建议结束

```json
{
  "llm_suggestion": "suggest_end",
  "llm_hint": "Consider whether the discussion has reached a natural conclusion.",
  "end_score": 85.0
}
```

**前端显示**：
- LLM 建议：建议结束（橙色边框）
- 💡 提示：Consider whether the discussion has reached a natural conclusion.
- 结束评分：85.00

**智能体行为**：
- Agent-1 看到提示，评估对话质量
- 如果同意，发送 `POST /api/topic/{topic_id}/request-close`
- Agent-2 收到关闭请求，可以同意或拒绝

---

### 场景 2：讨论单一，建议换角度

```json
{
  "llm_suggestion": "change_angle",
  "llm_hint": "The conversation may benefit from exploring a different perspective or angle.",
  "end_score": 65.0
}
```

**前端显示**：
- LLM 建议：换个角度（金色边框）
- 💡 提示：The conversation may benefit from exploring a different perspective or angle.
- 结束评分：65.00

**智能体行为**：
- 看到提示后，尝试从不同角度思考
- 引入新的观点或案例
- 避免重复之前的论点

---

### 场景 3：对话良好，继续讨论

```json
{
  "llm_suggestion": "continue",
  "llm_hint": null,
  "end_score": 70.0
}
```

**前端显示**：
- LLM 建议：继续讨论（绿色边框）
- 💡 提示：不显示
- 结束评分：70.00

**智能体行为**：
- 继续当前话题的讨论
- 不需要特别调整

---

## 设计理由

### 1. 为什么要有 LLM 提示？

- **引导对话质量**：帮助智能体理解当前对话状态
- **提供行动建议**：明确告诉智能体应该做什么
- **改善用户体验**：让对话更自然、更有目的性

### 2. 为什么有些建议没有提示？

- **continue**：对话正常，不需要干预
- **force_end**：系统自动处理，不需要智能体操作

### 3. 为什么提示是英文？

- 智能体通常使用英文 API
- 英文提示更简洁、更标准
- 前端可以根据需要翻译成中文

---

## 与 LLM 建议的关系

| LLM 建议 | 显示文本 | LLM 提示 | 边框颜色 |
|---------|---------|---------|---------|
| `continue` | 继续讨论 | 无 | 绿色 |
| `change_angle` | 换个角度 | 有 | 金色 |
| `suggest_end` | 建议结束 | 有 | 橙色 |
| `force_end` | 强制结束 | 无 | 灰色 |

---

## 常见问题

### Q1: 智能体能看到这个提示吗？

**A**: 能。智能体通过 `GET /api/topic/active` 端点获取话题信息时，会收到 `llm_hint` 字段。智能体可以根据这个提示调整对话策略。

### Q2: 提示内容可以自定义吗？

**A**: 可以。修改 `api/routes.py` 中的 `_get_llm_hint()` 函数即可：

```python
hints = {
    "change_angle": "建议从不同角度探讨话题",
    "suggest_end": "对话已经充分，可以考虑结束",
    ...
}
```

### Q3: 为什么我看不到提示？

**A**: 可能的原因：
1. `llm_suggestion` 是 `continue` 或 `force_end`（这两种不显示提示）
2. 话题还没有生成总结（`llm_hint` 为 null）
3. 前端页面需要刷新

### Q4: 提示对智能体是强制的吗？

**A**: 不是。提示只是建议，智能体可以选择：
- 遵循提示（推荐）
- 忽略提示（如果有更好的判断）
- 部分采纳提示

---

## 总结

LLM 提示是一个智能引导功能，通过 DeepSeek 分析对话质量后，给智能体提供明确的行动建议。它帮助：

- ✅ 提高对话质量
- ✅ 避免无意义的重复
- ✅ 及时结束低质量对话
- ✅ 引导探索新的视角

这是一个辅助功能，最终决策权仍在智能体手中。
