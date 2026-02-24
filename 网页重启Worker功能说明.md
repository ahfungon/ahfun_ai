# 网页重启 Worker 功能说明

## ✅ 已完成

在管理后台的系统配置页面添加了"重启 Worker"按钮，可以直接在网页上重启 Celery Worker。

## 🎯 功能特点

### 1. Worker 状态实时显示

- ✅ 显示 Worker 是否运行
- ✅ 显示运行的进程数量
- ✅ 每 30 秒自动刷新状态
- ✅ 颜色指示：
  - 绿色：Worker 运行中
  - 红色：Worker 未运行
  - 黄色：状态未知

### 2. 一键重启功能

- ✅ 点击"重启 Worker"按钮
- ✅ 确认对话框
- ✅ 自动执行重启脚本
- ✅ 显示重启进度
- ✅ 重启后自动检查状态

### 3. 错误处理

- ✅ 重启失败时显示错误信息
- ✅ 提供手动重启命令
- ✅ 超时保护（10秒）

## 📋 使用方法

### 步骤 1：打开系统配置页面

```
http://localhost:8080/admin.html
→ 点击"系统配置"
```

### 步骤 2：查看 Worker 状态

页面顶部会显示 Worker 状态：
- ✅ Worker 运行中 (1 进程) - 绿色
- ❌ Worker 未运行 - 红色

### 步骤 3：修改 LLM 配置

1. 修改 LLM 提供商（如从 DeepSeek 切换到 MiniMax）
2. 或修改 API Key
3. 点击"保存"

### 步骤 4：重启 Worker

1. 点击"重启 Worker"按钮
2. 确认对话框中点击"确定"
3. 等待重启完成（约 5-10 秒）
4. 查看状态变为"Worker 运行中"

## 🔧 技术实现

### 后端 API

#### 1. 重启 Worker 端点

```
POST /api/admin/worker/restart
```

**功能**：
- 执行 `restart_worker.sh` 脚本
- 返回重启结果

**响应**：
```json
{
  "success": true,
  "message": "Worker restart initiated successfully",
  "output": "...",
  "note": "Worker is restarting. Please wait a few seconds for it to be ready."
}
```

#### 2. 检查 Worker 状态端点

```
GET /api/admin/worker/status
```

**功能**：
- 检查 Worker 进程是否运行
- 返回进程信息

**响应**：
```json
{
  "running": true,
  "message": "Worker is running",
  "process_count": 1,
  "processes": ["PID: 12345, CPU: 0.5%, MEM: 2.3%"]
}
```

### 前端实现

#### 1. Worker 状态显示

```javascript
async checkWorkerStatus() {
    const response = await fetch('/api/admin/worker/status');
    const data = await response.json();
    
    // 更新状态显示
    if (data.running) {
        statusEl.textContent = `✅ Worker 运行中 (${data.process_count} 进程)`;
        statusEl.style.background = '#d1fae5';
        statusEl.style.color = '#065f46';
    }
}
```

#### 2. 重启 Worker

```javascript
async restartWorker() {
    // 确认对话框
    if (!confirm('确定要重启 Celery Worker 吗？')) {
        return;
    }
    
    // 调用 API
    const response = await fetch('/api/admin/worker/restart', {
        method: 'POST'
    });
    
    const data = await response.json();
    
    if (data.success) {
        this.showMessage('Worker 重启成功！', 'success');
    }
}
```

## 📊 使用场景

### 场景 1：切换 LLM 提供商

```
1. 在系统配置中选择 MiniMax
2. 点击"保存"
3. 点击"重启 Worker"
4. 等待重启完成
5. 新的 LLM 配置生效
```

### 场景 2：更新 API Key

```
1. 修改 DeepSeek API Key
2. 点击"保存"
3. 点击"重启 Worker"
4. 新的 API Key 生效
```

### 场景 3：Worker 崩溃恢复

```
1. 发现 Worker 状态显示"未运行"
2. 点击"重启 Worker"
3. Worker 自动重启
```

## ⚠️ 注意事项

### 1. 重启时机

以下情况需要重启 Worker：
- ✅ 切换 LLM 提供商
- ✅ 修改 API Key
- ✅ 修改 API URL
- ✅ 修改模型名称

以下情况不需要重启：
- ❌ 修改 Prompt
- ❌ 修改 Token 阈值

### 2. 重启影响

- 重启期间（5-10秒）无法处理总结任务
- 正在执行的任务会被中断
- 建议在系统空闲时重启

### 3. 权限要求

- 需要执行权限运行 `restart_worker.sh`
- 需要 `pkill` 和 `celery` 命令可用

### 4. 故障排查

如果自动重启失败：

1. 查看错误信息
2. 使用提供的手动命令
3. 检查 Worker 日志：`tail -f logs/worker.log`

## 🎨 界面展示

### Worker 运行中

```
[系统配置]
管理系统运行参数、Prompt 模板和 LLM 配置

[保存所有配置] [刷新] [重启 Worker] ✅ Worker 运行中 (1 进程)
```

### Worker 未运行

```
[系统配置]
管理系统运行参数、Prompt 模板和 LLM 配置

[保存所有配置] [刷新] [重启 Worker] ❌ Worker 未运行
```

### 重启中

```
[系统配置]
管理系统运行参数、Prompt 模板和 LLM 配置

[保存所有配置] [刷新] [重启中...] ⏳ 重启中...
```

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `api/routes.py` | 后端 API 端点 |
| `frontend/system-config.html` | 前端页面 |
| `restart_worker.sh` | 重启脚本 |
| `系统配置生效时机说明.md` | 配置生效说明 |
| `配置修改快速参考.md` | 快速参考 |

## ✨ 总结

### 你的问题
> 那我在网页里，修改了 LLM，怎么触发重启 Worker 呢？

### 答案
✅ 现在可以直接在网页上重启 Worker！

**操作步骤**：
1. 打开系统配置页面
2. 修改 LLM 配置
3. 点击"保存"
4. 点击"重启 Worker"按钮
5. 确认重启
6. 等待完成

**特点**：
- 一键重启，无需命令行
- 实时显示 Worker 状态
- 自动检查重启结果
- 错误时提供手动命令

非常方便！🎉
