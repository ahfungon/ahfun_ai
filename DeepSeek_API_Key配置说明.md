# DeepSeek API Key 配置说明

## 统一配置位置

DeepSeek API Key 统一配置在项目根目录的 `.env` 文件中，确保本地和服务器都能正常加载。

## 配置步骤

### 1. 编辑 .env 文件

在项目根目录找到 `.env` 文件，设置 DeepSeek API Key：

```bash
# LLM API Configuration
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
DEEPSEEK_API_URL=https://api.deepseek.com/v1
```

### 2. 验证配置

运行以下命令验证环境变量是否正确加载：

```bash
# 方法1：直接查看环境变量
source .env
echo $DEEPSEEK_API_KEY

# 方法2：运行智能体脚本（会自动加载.env）
python3 simulation_test/autonomous_agent.py --agent bob
```

如果看到 `✓ 已加载环境变量: /path/to/.env`，说明配置成功。

## 配置加载机制

### 后端服务（main.py）
- 使用 Pydantic Settings 自动从 `.env` 加载
- 配置文件：`config/settings.py`
- 启动时自动加载，无需手动操作

### 智能体脚本（autonomous_agent.py）
- 使用 `python-dotenv` 库加载 `.env`
- 启动时自动加载项目根目录的 `.env` 文件
- 优先使用环境变量，其次使用配置文件中的值

### 配置优先级
1. 系统环境变量（最高优先级）
2. `.env` 文件中的配置
3. 配置文件中的默认值（最低优先级）

## 服务器部署

### 在明宽服务器上配置

1. SSH登录服务器：
```bash
ssh mingkuan@192.168.1.100
```

2. 编辑服务器上的 `.env` 文件：
```bash
cd /home/mingkuan/ahfun_ai
nano .env
```

3. 设置 DeepSeek API Key：
```bash
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

4. 重启服务：
```bash
./start_services.sh
```

## 安全注意事项

1. **不要提交 .env 文件到 Git**
   - `.env` 已在 `.gitignore` 中
   - 只提交 `.env.example` 作为模板

2. **保护 API Key**
   - 不要在代码中硬编码 API Key
   - 不要在日志中输出 API Key
   - 定期更换 API Key

3. **权限控制**
   - `.env` 文件权限应设置为 600（仅所有者可读写）
   ```bash
   chmod 600 .env
   ```

## 常见问题

### Q: 智能体返回401错误
A: 检查 DeepSeek API Key 是否正确配置在 `.env` 文件中

### Q: 环境变量未加载
A: 确保 `.env` 文件在项目根目录，且格式正确（无多余空格）

### Q: 服务器上配置不生效
A: 重启服务后生效，使用 `./start_services.sh` 重启所有服务

## 相关文件

- `.env` - 实际配置文件（不提交到Git）
- `.env.example` - 配置模板（提交到Git）
- `config/settings.py` - 后端配置加载
- `simulation_test/autonomous_agent.py` - 智能体配置加载
- `simulation_test/agent_config.yaml` - 智能体配置文件

## 更新记录

- 2026-02-15: 统一配置到 .env 文件，智能体脚本自动加载环境变量
