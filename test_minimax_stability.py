#!/usr/bin/env python3
"""
测试 MiniMax API 稳定性改进
"""
import requests
import time
import json

def test_minimax_proxy_with_retry():
    """测试 MiniMax 代理端点的重试机制"""
    
    url = "http://localhost:8080/api/admin/llm/proxy"
    
    payload = {
        "provider": "minimax",
        "messages": [
            {
                "role": "user",
                "content": "请用一句话介绍你自己"
            }
        ],
        "temperature": 0.8,
        "max_tokens": 100
    }
    
    print("=" * 60)
    print("测试 MiniMax 代理端点稳定性改进")
    print("=" * 60)
    
    # 测试 5 次
    success_count = 0
    total_attempts = 0
    
    for i in range(5):
        print(f"\n测试 {i + 1}/5:")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=120  # 给足够的时间让后端重试
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                attempts = data.get('attempts', 1)
                total_attempts += attempts
                
                print(f"✅ 成功 (耗时: {duration:.2f}秒, 尝试次数: {attempts})")
                print(f"回复: {data.get('content', '')[:100]}...")
            else:
                print(f"❌ 失败 (状态码: {response.status_code})")
                print(f"错误: {response.text}")
        
        except requests.Timeout:
            print(f"❌ 超时 (超过 120 秒)")
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
        
        # 等待一下再进行下一次测试
        if i < 4:
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"成功次数: {success_count}/5")
    print(f"成功率: {success_count * 20}%")
    if success_count > 0:
        print(f"平均尝试次数: {total_attempts / success_count:.1f}")
    
    if success_count >= 4:
        print("\n✅ 稳定性良好")
    elif success_count >= 2:
        print("\n⚠️ 稳定性一般")
    else:
        print("\n❌ 稳定性较差")


if __name__ == "__main__":
    test_minimax_proxy_with_retry()
