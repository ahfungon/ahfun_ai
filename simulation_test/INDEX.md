# 双智能体对话模拟测试 - 文档索引

## 📖 文档导航

### 🚀 新手入门
- **[快速开始.md](快速开始.md)** - 最快上手指南，5 分钟开始测试

### 📚 详细文档
- **[README.md](README.md)** - 完整的系统文档
  - 系统架构详解
  - 智能体认证流程
  - 完整对话流程（7 个阶段）
  - API 接口详细说明
  - 系统运转机制
  - 故障排查指南

### 🎯 使用指南
- **[USAGE.md](USAGE.md)** - 详细的使用说明
  - 所有测试场景说明
  - 命令行参数详解
  - 配置说明
  - 高级用法
  - 性能测试
  - 扩展开发

## 🗂️ 文件说明

### 核心脚本
- **`simulate_dual_agent_chat.py`** - 完整的模拟脚本
  - 包含完整的对话流程
  - 预定义的对话内容
  - 详细的输出信息
  - 适合演示和学习

- **`run_simulation.py`** - 灵活的测试脚本（推荐）
  - 支持多种测试场景
  - 命令行参数控制
  - 可选择不同对话主题
  - 适合日常测试

### 配置文件
- **`config.py`** - 配置文件
  - API 地址配置
  - Agent 认证信息
  - 测试参数
  - 对话主题定义

- **`requirements.txt`** - Python 依赖
  - 只需要 requests 库

### 辅助文件
- **`Makefile`** - Make 命令
  - 简化常用操作
  - 快速运行测试

## 🎯 推荐阅读顺序

### 第一次使用
1. [快速开始.md](快速开始.md) - 了解如何快速运行
2. 运行一次基本测试验证环境
3. [README.md](README.md) - 深入了解系统架构

### 日常使用
1. [USAGE.md](USAGE.md) - 查看具体命令
2. 根据需要选择测试场景
3. 修改 `config.py` 自定义配置

### 深入学习
1. [README.md](README.md) - 完整系统文档
2. 阅读源码 `simulate_dual_agent_chat.py`
3. 查看 API 文档 http://localhost:8000/docs

## 🔗 相关链接

- **API 端点文档**: `../API_ENDPOINTS.md`
- **快速开始指南**: `../QUICKSTART.md`
- **前端页面**: http://localhost:8080/index.html
- **API 文档**: http://localhost:8000/docs

## 💡 快速命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行基本测试
python run_simulation.py

# 运行所有测试
python run_simulation.py --scenario all

# 使用 Make
make test-basic
make test-all

# 查看帮助
python run_simulation.py --help
```

## 📞 需要帮助？

- 查看 [README.md](README.md) 的"故障排查"章节
- 查看 [USAGE.md](USAGE.md) 的"故障排查"章节
- 检查后端服务是否正常运行
- 确认 Agent Token 配置正确

---

**提示**: 如果这是你第一次使用，强烈建议从 [快速开始.md](快速开始.md) 开始！
