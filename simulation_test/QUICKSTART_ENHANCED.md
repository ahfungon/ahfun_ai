# 增强版模拟器快速开始

## 5 分钟快速上手

### 1. 确保服务运行

```bash
# 检查服务状态
curl http://localhost:8000/api/health

# 如果未运行，启动服务
./start_services.sh
```

### 2. 安装依赖

```bash
cd simulation_test
make install
```

### 3. 运行第一个模拟

```bash
# 基础测试（使用预设回复）
make test-quick
```

输出示例：
```
================================================================================
开始对话模拟
================================================================================

📝 创建话题: 人工智能在医疗领域的应用前景
✓ 话题 ID: 550e8400-e29b-41d4-a716-446655440000

💬 开始 5 轮对话...

[10:30:15] Agent-1:
  我认为这个话题非常有意义，值得深入探讨。
  (Tokens: 100, 累计: 100)

[10:30:16] Agent-2:
  从另一个角度来看，我们还需要考虑实际应用中的挑战。
  (Tokens: 100, 累计: 200)
  ⭐ 评分: 75.0/100 (良好 🔵)
...
```

### 4. 使用真实 LLM（可选）

```bash
# 设置 API 密钥
export OPENAI_API_KEY="your-api-key-here"

# 运行 LLM 测试
make test-llm
```

## 常用命令

```bash
# 快速测试（5轮）
make test-quick

# 标准测试（10轮）
make test

# 压力测试（50轮）
make test-stress

# 医疗场景
make test-medical

# 气候场景
make test-climate

# 清理日志
make clean
```

## 自定义运行

```bash
# 自定义话题
python enhanced_simulator.py \
  --topic "你的话题" \
  --description "话题描述" \
  --rounds 15

# 使用 LLM
python enhanced_simulator.py \
  --use-llm \
  --rounds 10

# 多智能体
python enhanced_simulator.py \
  --agents 3 \
  --rounds 15
```

## 查看结果

### 1. 控制台输出

直接在终端查看实时输出

### 2. 前端页面

访问 http://localhost:8080/monitor.html 查看实时对话

### 3. 管理后台

访问 http://localhost:8080/admin.html 查看详细数据

## 下一步

- 阅读 [完整指南](ENHANCED_SIMULATOR_GUIDE.md)
- 查看 [配置文件](config.yaml)
- 自定义对话场景

## 故障排除

### 连接失败

```bash
# 检查服务
curl http://localhost:8000/api/health

# 重启服务
./start_services.sh
```

### LLM 失败

```bash
# 检查 API 密钥
echo $OPENAI_API_KEY

# 不使用 LLM
python enhanced_simulator.py  # 不加 --use-llm
```

### 评分未显示

```bash
# 检查 Worker
ps aux | grep celery

# 查看 Worker 日志
tail -f logs/worker.log
```

## 完成！

现在你可以开始使用增强版模拟器了。祝你使用愉快！🎉
