#!/usr/bin/env python3
"""
验证时区修复

检查 API 返回的时间是否包含时区标识符 'Z'
"""

import requests
from datetime import datetime

def test_timezone_fix():
    print("🔍 验证时区修复...")
    print()
    
    # 注册临时智能体
    agent = requests.post(
        'http://localhost:8000/api/agent/register',
        json={'agent_name': 'Timezone-Verify'}
    ).json()
    
    # 获取消息
    response = requests.get(
        'http://localhost:8000/api/topic/f99d2540-7911-4c26-9bd8-2d3a92bef5c6/messages',
        headers={
            'X-Agent-Id': agent['agent_id'],
            'X-Auth-Token': agent['auth_token']
        },
        params={'limit': 1}
    )
    
    messages = response.json()['messages']
    
    if not messages:
        print("❌ 没有消息")
        return False
    
    msg = messages[0]
    created_at = msg['created_at']
    
    print(f"📝 消息时间: {created_at}")
    print()
    
    # 检查是否有时区标识符
    has_timezone = created_at.endswith('Z') or '+' in created_at
    
    if has_timezone:
        print("✅ 时区标识符已添加")
    else:
        print("❌ 时区标识符缺失")
        return False
    
    # 解析时间
    try:
        # JavaScript 会自动解析带 Z 的时间
        from datetime import timezone, timedelta
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        print(f"✅ 时间可以正确解析")
        print()
        
        # 显示本地时间（CST = UTC+8）
        cst = timezone(timedelta(hours=8))
        local_time = dt.astimezone(cst)
        
        print(f"📊 时间对比:")
        print(f"   UTC 时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   CST 时间: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   时差: +8 小时")
        print()
        
        print("✅ 前端将自动转换为本地时间")
        return True
        
    except Exception as e:
        print(f"❌ 时间解析失败: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_timezone_fix()
        if success:
            print()
            print("=" * 60)
            print("🎉 时区修复验证成功！")
            print("=" * 60)
            print()
            print("前端现在应该能正确显示时间了。")
            print("请刷新 monitor.html 页面查看效果。")
        else:
            print()
            print("=" * 60)
            print("❌ 时区修复验证失败")
            print("=" * 60)
    except Exception as e:
        print(f"❌ 验证出错: {e}")
