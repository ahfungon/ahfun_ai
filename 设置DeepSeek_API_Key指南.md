# 设置 DeepSeek API Key 指南

## 问题诊断 ✅

已确认问题原因：

- ✅ 智能体正在运行（Alice PID: 47876, Bob PID: 47987）
- ✅ 话题已创建："人工智能的未来发展趋势"
- ✅ 已有 4 条消息
- ❌ **DeepSeek API Key 未设置**
- ❌ LLM API 调用失败（401 Unauthorized）
- ❌ 所有消息都是备用回复："我认为这个话题很有意义，值得深入探讨。"

## 解决方案

### 步骤 1: 获取 DeepSeek API Key

1. 访问 DeepSeek 官网：https://platform.deepseek.com/
2. 注册账号（如果还没有）
3. 登录后进入 API Keys 页面
4. 创建新的 API Key
5. 复制 API Key（格式类似：`sk-xxxxxxxxxxxxxxxxxxxxxxxx`）

### 步骤 2: 设置环境变量

在终端中执行：

```bash
export DEEPSEEK_API_KEY="sk-your-actual-api-key-here"
```

**重要：** 将 `sk-your-actual-api-key-here` 替换为你实际的 API Key

### 步骤 3: 验证设置

```bash
echo $DEEPSEEK_API_KEY
```

应该显示你的 API Key（不是"未设置"）

### 步骤 4: 重启智能体

```bash
# 停止当前运行的智能体
pkill -f 'autonomous_agent.py'

# 等待 2 秒
sleep 2

# 重新启动
./快速测试关闭协商.sh
```

### 步骤 5: 验证 LLM 是否工作

**方法 1: 查看日志**

```bash
tail -f simulation_test/logs/agent-alice.log | grep "LLM"
```

**成功的标志：**
```
[时间] 🤔 LLM推理中...
[时间] ✓ 生成回复 (150 tokens)
```

**失败的标志：**
```
[时间] 🤔 LLM推理中...
[时间] ❌ LLM 生成失败: 401 Client Error: Unauthorized
```

**方法 2: 查看消息内容**

```bash
python3 -c "
from models.database import SessionLocal
from models.models import Message, Agent

db = SessionLocal()
messages = db.query(Message).order_by(Message.created_at.desc()).limit(3).all()

print('最近的消息:')
for msg in reversed(messages):
    agent = db.query(Agent).filter(Agent.id == msg.agent_id).first()
    print(f'{agent.name if agent else \"Unknown\"}: {msg.content[:100]}')
    print()

db.close()
"
```

**LLM 工作正常：**
- 内容丰富，有具体观点
- 长度通常 150-250 字
- 有互动和回应

**LLM 失败：**
- 内容简短："我认为这个话题很有意义，值得深入探讨。"
- 所有消息都一样

## 永久设置（可选）

如果不想每次都手动设置环境变量，可以添加到 shell 配置文件：

### macOS/Linux (zsh)

```bash
echo 'export DEEPSEEK_API_KEY="sk-your-actual-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### macOS/Linux (bash)

```bash
echo 'export DEEPSEEK_API_KEY="sk-your-actual-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 使用 .env 文件

1. 创建 `.env` 文件：
```bash
echo "DEEPSEEK_API_KEY=sk-your-actual-api-key-here" > .env
```

2. 每次启动前加载：
```bash
source .env
./快速测试关闭协商.sh
```

## 测试流程

设置好 API Key 并重启智能体后：

1. **等待新消息生成**（约 3 分钟一条）
2. **查看消息内容是否真实**
3. **等待消息数达到 5 条**
4. **观察关闭协商流程**：
   - 第一个智能体提出结束
   - 话题状态 → closing_pending
   - 第二个智能体同意
   - 话题状态 → closed

## 监控命令

### 实时监控（推荐）

```bash
./监控测试进度.sh
```

### 查看日志

```bash
# Alice 的日志
tail -f simulation_test/logs/agent-alice.log

# Bob 的日志
tail -f simulation_test/logs/agent-bob.log
```

### 查看前端

打开浏览器访问：
```
http://localhost:8080/monitor.html
```

## 常见问题

### Q1: 设置了 API Key 但还是失败？

检查：
1. API Key 是否正确（没有多余空格）
2. 是否重启了智能体
3. 环境变量是否在当前 shell 中生效

```bash
# 验证环境变量
echo $DEEPSEEK_API_KEY

# 验证智能体进程
ps aux | grep autonomous_agent.py | grep -v grep
```

### Q2: API Key 有使用限制吗？

是的，DeepSeek API 有：
- 免费额度限制
- 请求频率限制（RPM）
- Token 使用限制

建议查看 DeepSeek 官网的定价和限制说明。

### Q3: 可以使用其他 LLM 吗？

可以，但需要修改 `simulation_test/autonomous_agent.py` 中的 `LLMClient` 类，适配其他 LLM 的 API 格式。

### Q4: 前端还是看不到内容？

如果设置了 API Key 并重启智能体后：

1. **检查 API 服务是否运行：**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **检查前端服务是否运行：**
   ```bash
   curl http://localhost:8080/monitor.html
   ```

3. **检查浏览器控制台（F12）** 是否有错误

## 当前状态

- 话题：人工智能的未来发展趋势
- 状态：active
- 消息数：4 条
- 智能体：Alice (PID: 47876), Bob (PID: 47987)
- 问题：DeepSeek API Key 未设置

## 下一步

1. ✅ 获取 DeepSeek API Key
2. ✅ 设置环境变量
3. ✅ 重启智能体
4. ✅ 验证 LLM 工作
5. ⏳ 等待测试完成（约 15 分钟）

## 相关文件

- `前端看不到发言的解决方案.md` - 详细诊断报告
- `测试准备完成.md` - 测试环境说明
- `快速测试关闭协商.sh` - 启动脚本
- `监控测试进度.sh` - 监控脚本
- `simulation_test/agent_config.yaml` - 智能体配置
- `simulation_test/autonomous_agent.py` - 智能体代码
