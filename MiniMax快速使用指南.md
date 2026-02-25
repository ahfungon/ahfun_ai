# MiniMax 快速使用指南

## 🚀 5 分钟快速上手

### 1. 检查配置状态

```bash
python diagnose_llm_provider.py
```

**预期输出**:
```
✅ 已配置使用 MiniMax
✅ Worker 正在运行
```

---

### 2. 使用前端模拟器

**步骤**:
1. 访问: http://localhost:8080/admin.html
2. 点击"智能体模拟器"标签
3. 点击"添加智能体"
4. 填写智能体信息:
   - 名称: 任意名称（如"测试智能体"）
   - 发言模式: 选择"MiniMax 调用"
5. 点击"添加"
6. 点击"启动智能体"
7. 智能体会自动使用 MiniMax 生成回复

**特点**:
- ✅ 自动过滤思考标签
- ✅ 失败时降级到模板模式
- ✅ 实时显示日志

---

### 3. 配置消息评分和总结

**步骤**:
1. 访问: http://localhost:8080/system-config.html
2. 找到"LLM 配置"部分
3. 设置:
   - 消息评分 LLM 提供商: `minimax`
   - 对话总结 LLM 提供商: `minimax`
4. 点击"保存配置"
5. 点击"重启 Worker"按钮
6. 等待 10-15 秒

**验证**:
```bash
python diagnose_llm_provider.py
```

---

## 📋 常用命令

### 诊断配置
```bash
python diagnose_llm_provider.py
```

### 测试代理端点
```bash
python test_llm_proxy.py
```

### 测试思考标签过滤
```bash
python test_minimax_filter.py
```

### 重启 Worker
```bash
bash restart_worker_quick.sh
```

### 查看 Worker 日志
```bash
tail -f logs/worker.log | grep -i minimax
```

---

## ⚠️ 重要提示

### 1. 修改配置后必须重启 Worker

**原因**: Worker 在启动时读取配置

**重启方法**:
- 在系统配置页面点击"重启 Worker"按钮
- 或运行: `bash restart_worker_quick.sh`

### 2. API Key 和域名必须匹配

| API Key 格式 | 域名 |
|-------------|------|
| `sk-cp-xxx...` | `api.minimax.chat` ✅ |
| `sk-xxx...` | `api.minimaxi.com` |

**当前配置**: 旧格式 Key + 旧域名 ✅

### 3. 思考标签会被自动过滤

MiniMax 的 `<think>` 标签会被自动过滤，只显示最终回复。

---

## 🔧 故障排查

### 问题: 前端模拟器调用失败

**解决**:
```bash
# 1. 检查后端服务
curl http://localhost:8080/health

# 2. 测试代理端点
python test_llm_proxy.py

# 3. 查看浏览器控制台错误
```

### 问题: 评分和总结没有使用 MiniMax

**解决**:
```bash
# 1. 诊断配置
python diagnose_llm_provider.py

# 2. 重启 Worker
bash restart_worker_quick.sh

# 3. 查看日志
tail -f logs/worker.log | grep -i minimax
```

### 问题: API URL 错误

**解决**:
```bash
# 自动修复
python fix_minimax_url.py

# 重启 Worker
bash restart_worker_quick.sh
```

---

## 📚 相关文档

- **MiniMax完整集成验证报告.md** - 完整验证报告
- **MiniMax完整集成总结.md** - 集成总结
- **MiniMax评分总结配置问题修复.md** - 配置问题修复
- **API_ENDPOINTS.md** - API 文档

---

## 📞 需要帮助？

1. 查看完整文档: `MiniMax完整集成验证报告.md`
2. 运行诊断工具: `python diagnose_llm_provider.py`
3. 查看 Worker 日志: `tail -f logs/worker.log`

---

**快速上手完成！** 🎉

现在你可以:
- ✅ 使用前端模拟器测试 MiniMax
- ✅ 配置消息评分使用 MiniMax
- ✅ 配置对话总结使用 MiniMax
- ✅ 诊断和排查问题
