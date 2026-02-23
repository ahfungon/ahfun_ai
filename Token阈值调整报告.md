# Token 阈值调整报告

## 调整内容

将摘要触发的 Token 阈值从 **8000** 降低到 **4000**

## 修改范围

### 1. 本地环境
- **文件**: `.env`
- **修改**: `SUMMARY_THRESHOLD=8000` → `SUMMARY_THRESHOLD=4000`
- **验证**: ✓ 本地阈值: 4000

### 2. 生产环境（明宽服务器）
- **文件**: `~/dual-agent-chat/.env`
- **修改**: `SUMMARY_THRESHOLD=8000` → `SUMMARY_THRESHOLD=4000`
- **验证**: ✓ 当前阈值: 4000
- **服务重启**: 
  - ✓ dual-agent-api (已重启)
  - ✓ dual-agent-celery (已重启)

### 3. 文档更新
- **文件**: `摘要触发机制说明.md`
- **修改**: 所有提到 8000 的地方更新为 4000

## 新的触发机制

### 触发条件
当满足以下所有条件时，系统会自动触发摘要生成：

1. ✓ 话题状态为 `active`
2. ✓ `token_count_since_summary` >= **4000** (原 8000)
3. ✓ `pending_summary_job` = `false`

### 触发频率变化

| 项目 | 原配置 (8000) | 新配置 (4000) | 变化 |
|------|--------------|--------------|------|
| 触发阈值 | 8000 tokens | 4000 tokens | -50% |
| 预计触发频率 | 较低 | 提高 2 倍 | +100% |
| 摘要生成次数 | 较少 | 增加 | ↑ |
| LLM API 调用 | 较少 | 增加 | ↑ |

## 影响分析

### 正面影响

1. **更及时的摘要**
   - 对话进行到 4000 tokens 就会生成摘要
   - 更早获得 LLM 的建议和评分

2. **更频繁的状态评估**
   - 更及时地判断话题是否应该结束
   - 减少无效对话的持续时间

3. **更好的对话控制**
   - 智能体可以更早地获得系统建议
   - 有助于及时调整对话方向

### 潜在影响

1. **API 调用增加**
   - DeepSeek API 调用频率提高约 2 倍
   - 需要关注 API 配额和成本

2. **系统负载**
   - Celery Worker 处理摘要任务的频率增加
   - 需要监控 Worker 性能

3. **数据库写入**
   - 摘要历史记录增加
   - summary_history 表增长速度加快

## 验证结果

### 本地环境
```bash
$ python3 -c "from config.settings import settings; print(f'本地阈值: {settings.summary_threshold}')"
本地阈值: 4000
```

### 生产环境
```bash
$ ssh ubuntu@129.211.28.211 "cd ~/dual-agent-chat && source venv/bin/activate && python3 -c 'from config.settings import settings; print(f\"当前阈值: {settings.summary_threshold}\")'"
当前阈值: 4000
```

### 服务状态
```bash
● dual-agent-api.service - Dual Agent Chat API
     Active: active (running)

● dual-agent-celery.service - Dual Agent Chat Celery Worker
     Active: active (running)
```

## 监控建议

### 1. API 使用监控
```bash
# 监控 DeepSeek API 调用频率
tail -f logs/worker.log | grep -i "deepseek"
```

### 2. 摘要生成监控
```sql
-- 查看最近的摘要生成
SELECT topic_id, created_at, status 
FROM summary_jobs 
ORDER BY created_at DESC 
LIMIT 10;

-- 统计每小时的摘要数量
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as summary_count
FROM summary_jobs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

### 3. Token 计数监控
```bash
# 监控话题的 token 计数
curl http://129.211.28.211:8080/api/monitor/topic/active | jq '.token_count_since_summary'
```

## 回滚方案

如果需要回滚到原来的 8000 阈值：

### 本地环境
```bash
# 修改 .env
sed -i '' 's/SUMMARY_THRESHOLD=4000/SUMMARY_THRESHOLD=8000/g' .env

# 重启服务（如果在运行）
pkill -f "uvicorn main:app"
pkill -f "celery.*worker"
```

### 生产环境
```bash
ssh -i ~/.ssh/mingkuan.pem ubuntu@129.211.28.211 << 'EOF'
cd ~/dual-agent-chat
sed -i 's/SUMMARY_THRESHOLD=4000/SUMMARY_THRESHOLD=8000/g' .env
sudo systemctl restart dual-agent-api
sudo systemctl restart dual-agent-celery
EOF
```

## 后续观察

### 观察期: 1-2 天

需要关注以下指标：

1. **摘要质量**
   - 4000 tokens 的对话是否足够生成有意义的摘要
   - LLM 建议的准确性

2. **系统性能**
   - Celery Worker 的处理能力
   - API 响应时间
   - 数据库性能

3. **用户体验**
   - 智能体是否能更好地控制对话
   - 话题关闭的及时性

4. **成本**
   - DeepSeek API 调用次数
   - 相关费用变化

## Git 提交

```bash
commit 1a04721
Author: [Your Name]
Date:   Sun Feb 15 19:23:00 2026

    将摘要触发阈值从8000降低到4000 tokens
    
    - 修改本地 .env: SUMMARY_THRESHOLD=4000
    - 修改服务器 .env: SUMMARY_THRESHOLD=4000
    - 更新文档: 摘要触发机制说明.md
    - 重启生产环境服务
```

## 总结

✅ **修改完成**
- 本地环境: 4000 tokens
- 生产环境: 4000 tokens
- 文档已更新
- 服务已重启

✅ **验证通过**
- 配置加载正确
- 服务运行正常
- 环境一致

⚠️ **需要关注**
- API 调用频率
- 系统性能
- 摘要质量

---

**调整时间**: 2026-02-15 19:23 CST
**调整人员**: System Administrator
**状态**: ✅ 已完成并验证
