#!/bin/bash

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 智能体状态诊断"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. 检查环境变量
echo "【1. 环境变量检查】"
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ DEEPSEEK_API_KEY 未设置"
    echo "   请执行: export DEEPSEEK_API_KEY=\"your-api-key\""
else
    KEY_LENGTH=${#DEEPSEEK_API_KEY}
    KEY_PREVIEW="${DEEPSEEK_API_KEY:0:10}...${DEEPSEEK_API_KEY: -4}"
    echo "✅ DEEPSEEK_API_KEY 已设置"
    echo "   长度: $KEY_LENGTH 字符"
    echo "   预览: $KEY_PREVIEW"
fi
echo ""

# 2. 检查智能体进程
echo "【2. 智能体进程检查】"
AGENT_PIDS=$(ps aux | grep 'autonomous_agent.py' | grep -v grep | awk '{print $2}')
if [ -z "$AGENT_PIDS" ]; then
    echo "❌ 没有运行中的智能体"
    echo "   请执行: ./快速测试关闭协商.sh"
else
    echo "✅ 智能体正在运行:"
    ps aux | grep 'autonomous_agent.py' | grep -v grep | while read line; do
        PID=$(echo $line | awk '{print $2}')
        AGENT=$(echo $line | grep -o '\--agent [a-z]*' | awk '{print $2}')
        AGENT_NAME=$(echo $AGENT | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')
        echo "   - Agent-${AGENT_NAME} (PID: $PID)"
    done
fi
echo ""

# 3. 检查 API 服务
echo "【3. API 服务检查】"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ API 服务正常 (http://localhost:8000)"
else
    echo "❌ API 服务未响应"
    echo "   请检查服务是否启动"
fi
echo ""

# 4. 检查前端服务
echo "【4. 前端服务检查】"
if curl -s http://localhost:8080/monitor.html > /dev/null 2>&1; then
    echo "✅ 前端服务正常 (http://localhost:8080)"
else
    echo "❌ 前端服务未响应"
    echo "   请检查服务是否启动"
fi
echo ""

# 5. 检查话题和消息
echo "【5. 话题和消息检查】"
python3 -c "
from models.database import SessionLocal
from models.models import Topic, Message, Agent

db = SessionLocal()

topic = db.query(Topic).order_by(Topic.created_at.desc()).first()

if topic:
    print(f'✅ 话题: {topic.title}')
    print(f'   状态: {topic.status}')
    print(f'   话题ID: {topic.id}')
    
    messages = db.query(Message).filter(Message.topic_id == topic.id).order_by(Message.created_at).all()
    print(f'   消息数: {len(messages)}')
    print()
    
    if messages:
        print('   最近的消息:')
        for msg in messages[-3:]:
            agent = db.query(Agent).filter(Agent.id == msg.agent_id).first()
            agent_name = agent.name if agent else 'Unknown'
            content_preview = msg.content[:60].replace('\n', ' ')
            print(f'   - {agent_name}: {content_preview}...')
else:
    print('❌ 没有活跃话题')

db.close()
" 2>/dev/null
echo ""

# 6. 检查 LLM 状态
echo "【6. LLM 调用状态检查】"
if [ -f "simulation_test/logs/agent-alice.log" ]; then
    LAST_LLM_ERROR=$(tail -50 simulation_test/logs/agent-alice.log | grep "LLM 生成失败" | tail -1)
    LAST_LLM_SUCCESS=$(tail -50 simulation_test/logs/agent-alice.log | grep "生成回复" | tail -1)
    
    if [ -n "$LAST_LLM_ERROR" ]; then
        echo "❌ LLM 调用失败"
        echo "   错误: $(echo $LAST_LLM_ERROR | sed 's/.*❌ //')"
        echo ""
        echo "   可能原因:"
        echo "   1. API Key 未设置或无效"
        echo "   2. API 额度不足"
        echo "   3. 网络连接问题"
    elif [ -n "$LAST_LLM_SUCCESS" ]; then
        echo "✅ LLM 调用正常"
        echo "   最近: $(echo $LAST_LLM_SUCCESS | sed 's/.*✓ //')"
    else
        echo "⚠️  无法确定 LLM 状态（日志不足）"
    fi
else
    echo "⚠️  日志文件不存在"
fi
echo ""

# 7. 检查消息内容质量
echo "【7. 消息内容质量检查】"
python3 -c "
from models.database import SessionLocal
from models.models import Message, Agent

db = SessionLocal()
messages = db.query(Message).order_by(Message.created_at.desc()).limit(5).all()

if messages:
    # 检查是否都是备用回复
    fallback_count = sum(1 for msg in messages if '我认为这个话题很有意义，值得深入探讨' in msg.content)
    
    if fallback_count == len(messages):
        print('❌ 所有消息都是备用回复')
        print('   说明: LLM 未正常工作，使用了备用回复')
        print('   原因: DeepSeek API Key 未设置或无效')
        print()
        print('   解决方案:')
        print('   1. 设置 API Key: export DEEPSEEK_API_KEY=\"your-key\"')
        print('   2. 重启智能体: pkill -f autonomous_agent.py && ./快速测试关闭协商.sh')
    elif fallback_count > 0:
        print(f'⚠️  部分消息是备用回复 ({fallback_count}/{len(messages)})')
        print('   说明: LLM 间歇性失败')
    else:
        print('✅ 消息内容正常')
        print('   说明: LLM 正常生成对话内容')
        print()
        print('   最近的消息:')
        for msg in reversed(messages[:3]):
            agent = db.query(Agent).filter(Agent.id == msg.agent_id).first()
            content_preview = msg.content[:80].replace('\n', ' ')
            print(f'   - {agent.name if agent else \"Unknown\"}: {content_preview}...')
else:
    print('⚠️  没有消息')

db.close()
" 2>/dev/null
echo ""

# 8. 总结和建议
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "【诊断总结】"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "🔧 需要设置 DeepSeek API Key:"
    echo ""
    echo "   1. 获取 API Key: https://platform.deepseek.com/"
    echo "   2. 设置环境变量: export DEEPSEEK_API_KEY=\"your-key\""
    echo "   3. 重启智能体: pkill -f autonomous_agent.py && ./快速测试关闭协商.sh"
    echo "   4. 验证状态: ./诊断智能体状态.sh"
    echo ""
    echo "   详细说明: 查看 设置DeepSeek_API_Key指南.md"
else
    echo "✅ 环境配置正常"
    echo ""
    echo "   监控命令:"
    echo "   - 实时监控: ./监控测试进度.sh"
    echo "   - 查看日志: tail -f simulation_test/logs/agent-alice.log"
    echo "   - 前端页面: http://localhost:8080/monitor.html"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
