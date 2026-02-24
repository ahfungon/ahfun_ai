# 模拟器 LLM 配置快速指南

## 问题：配置太乱了？

之前你可能遇到过：
- ❌ 在管理后台配置了 API Key，但模拟器用不了
- ❌ 需要在多个地方重复配置（.env、config.yaml、系统配置）
- ❌ 不知道模拟器到底用的是哪个配置

## 解决方案：统一配置

现在所有模块都使用系统配置（数据库），一处配置，全局生效！

---

## 快速开始

### 步骤 1: 在管理后台配置 LLM

1. 访问：http://localhost:8080/system-config.html
2. 找到"LLM 配置"部分
3. 配置以下项目：
   - **LLM 提供商**：选择 DeepSeek 或 MiniMax
   - **DeepSeek API Key**：填入你的 API Key（如果选择 DeepSeek）
   - **MiniMax API Key**：填入你的 API Key（如果选择 MiniMax）
4. 点击"保存所有配置"

### 步骤 2: 运行 Python 模拟器

```bash
python simulation_test/enhanced_simulator.py --use-llm --rounds 5
```

**就这么简单！** 模拟器会自动从系统配置获取 LLM 设置。

---

## 配置优先级

Python 模拟器会按以下顺序查找配置：

1. 🥇 **系统配置**（数据库）- 推荐，自动同步
2. 🥈 **环境变量**（DEEPSEEK_API_KEY）- 备用
3. 🥉 **配置文件**（config.yaml）- 备用

**建议**：只在管理后台配置，其他地方不用管！

---

## 验证配置

### 方法 1: 运行测试脚本

```bash
python test_llm_config_unified.py
```

**输出示例**：
```
✓ API 端点可访问
✓ 返回数据格式正确
✓ LLM 已配置
  系统配置中有有效的 API Key

配置信息:
  - 提供商: minimax
  - API URL: https://api.minimax.chat/v1
  - 模型: abab6.5-chat
  - 脱敏 Key: 134...xxx
  - 已配置: True
```

### 方法 2: 查看模拟器日志

运行模拟器时，查看日志输出：

```
✓ 从系统配置获取 LLM 配置: minimax (134...xxx)
✓ LLM 后端已启用 (系统配置: minimax)
```

如果看到这两行，说明配置成功！

---

## 常见问题

### Q1: 我修改了配置，需要重启什么吗？

**A**: 
- ✅ Python 模拟器：无需重启，下次运行自动获取新配置
- ⚠️ 后端服务（消息评分、对话总结）：需要重启 Worker

**重启 Worker**：
1. 访问管理后台：http://localhost:8080/system-config.html
2. 点击"重启 Worker"按钮
3. 等待 10-15 秒

### Q2: 模拟器还是用不了 LLM？

**检查清单**：
1. 后端服务是否运行？
   ```bash
   curl http://localhost:8000/api/health
   ```

2. 系统配置是否有 API Key？
   ```bash
   python test_llm_config_unified.py
   ```

3. 是否使用了 `--use-llm` 参数？
   ```bash
   python simulation_test/enhanced_simulator.py --use-llm --rounds 5
   ```

### Q3: 我还需要配置环境变量吗？

**A**: 不需要！系统配置优先级最高。

但如果你想保留备用方案（系统配置不可用时使用），可以设置：
```bash
export DEEPSEEK_API_KEY=sk-xxx
```

### Q4: 前端模拟器支持 LLM 吗？

**A**: 暂不支持。前端模拟器目前使用预设模板生成消息。

如果需要 LLM 支持，请使用 Python 模拟器。

---

## 配置示例

### DeepSeek 配置

在管理后台配置：
- **LLM 提供商（评分）**: deepseek
- **LLM 提供商（总结）**: deepseek
- **DeepSeek API Key**: sk-xxxxxxxxxxxxxxxx

### MiniMax 配置

在管理后台配置：
- **LLM 提供商（评分）**: minimax
- **LLM 提供商（总结）**: minimax
- **MiniMax API Key**: 你的 MiniMax API Key

---

## 对比：之前 vs 现在

### 之前（配置分散）

```bash
# 1. 在 .env 文件配置
DEEPSEEK_API_KEY=sk-xxx

# 2. 在 config.yaml 配置
llm:
  api_key: sk-xxx
  api_url: https://api.deepseek.com/v1

# 3. 在管理后台配置
# ...

# 4. 运行模拟器
python simulation_test/enhanced_simulator.py --use-llm
```

❌ 需要在 3 个地方配置  
❌ 配置不同步  
❌ 容易出错  

### 现在（配置统一）

```bash
# 1. 在管理后台配置（一次）
# http://localhost:8080/system-config.html

# 2. 运行模拟器
python simulation_test/enhanced_simulator.py --use-llm
```

✅ 只需在 1 个地方配置  
✅ 自动同步  
✅ 简单可靠  

---

## 总结

**记住这 3 点**：

1. 🎯 **只在管理后台配置** - 一处配置，全局生效
2. 🔄 **自动同步** - 修改后无需手动更新
3. 🛡️ **有备用方案** - 系统配置不可用时自动回退

**开始使用**：
```bash
# 1. 配置（管理后台）
http://localhost:8080/system-config.html

# 2. 运行（Python 模拟器）
python simulation_test/enhanced_simulator.py --use-llm --rounds 5

# 3. 验证（测试脚本）
python test_llm_config_unified.py
```

就这么简单！🎉
