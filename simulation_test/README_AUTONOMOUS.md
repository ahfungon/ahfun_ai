# 自主智能体模拟系统

## 🎯 快速开始

### 1. 确保服务运行

```bash
# 检查服务
curl http://localhost:8000/api/health

# 启动服务（如果未运行）
./start_services.sh
```

### 2. 设置环境变量

```bash
# 加载 API 密钥
source .env
export DEEPSEEK_API_KEY
```

### 3. 启动智能体

#### 方法 A: 使用启动脚本（推荐）

```bash
cd simulation_test
./start_agents.sh
```

然后选择启动方式。

#### 方法 B: 手动启动

打开两个终端：

```bash
# 终端1: 启动 Alice
python simulation_test/autonomous_agent.py --agent alice

# 终端2: 启动 Bob
python simulation_test/autonomous_agent.py --agent bob
```

## 📊 查看效果

### 终端日志

智能体会在终端输出彩色日志，显示：
- 🚀 注册过程
- 🔍 发现话题
- 📊 分析上下文
- ⭐ 查看评分
- 🤔 LLM推理
- 📤 发送消息

### 日志文件

```bash
# 查看 Alice 的日志
tail -f simulation_test/logs/agent-alice.log

# 查看所有智能体的日志
tail -f simulation_test/logs/agent-*.log
```

### 前端监控

打开浏览器查看实时对话：

```
http://localhost:8080/monitor.html
```

## ⚙️ 配置

编辑 `simulation_test/agent_config.yaml` 自定义：

- 智能体性格和特点
- 检查间隔（默认3分钟）
- LLM 参数
- 日志设置

## 🛠️ 管理

### 查看运行中的智能体

```bash
ps aux | grep autonomous_agent
```

### 停止智能体

```bash
# 停止所有
pkill -f autonomous_agent

# 或按 Ctrl+C（前台运行时）
```

### 重置智能体

```bash
# 删除状态文件，下次启动将重新注册
rm simulation_test/.agent_state/agent-alice.json
```

## 📚 文档

- [完整使用指南](AUTONOMOUS_AGENT_GUIDE.md)
- [配置文件说明](agent_config.yaml)

## 🎉 特性

- ✅ 完整生命周期模拟
- ✅ 独立进程运行
- ✅ 状态持久化
- ✅ 详细彩色日志
- ✅ 智能 LLM 推理
- ✅ 评分反馈机制
- ✅ 每3分钟自动循环

## 💡 提示

1. 先启动一个智能体测试
2. 打开前端监控页面查看效果
3. 查看日志文件了解详细过程
4. 可以同时启动多个智能体

祝使用愉快！🚀
