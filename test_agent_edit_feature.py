#!/usr/bin/env python3
"""
测试智能体编辑功能
"""
import requests
import json
import hashlib

BASE_URL = "http://localhost:8080"

def hash_token(token: str) -> str:
    """生成 token 的 SHA-256 哈希"""
    return hashlib.sha256(token.encode()).hexdigest()

def test_register_agent_with_system_prompt():
    """测试注册带系统提示词的智能体"""
    print("\n=== 测试1: 注册带系统提示词的智能体 ===")
    
    agent_data = {
        "agent_name": "测试智能体",
        "auth_token": "test_token_123",
        "system_prompt": "你是一个友好的助手，说话风格幽默风趣。"
    }
    
    response = requests.post(f"{BASE_URL}/api/agent/register", json=agent_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        agent_id = response.json()["agent_id"]
        print(f"✓ 智能体注册成功，ID: {agent_id}")
        return agent_id
    else:
        print("✗ 智能体注册失败")
        return None

def test_get_agent_info(agent_id: str):
    """测试获取智能体信息"""
    print(f"\n=== 测试2: 获取智能体信息 ===")
    
    response = requests.get(f"{BASE_URL}/api/admin/agents")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        agents = data.get("agents", [])
        agent = next((a for a in agents if a["agent_id"] == agent_id), None)
        
        if agent:
            print(f"响应: {json.dumps(agent, indent=2, ensure_ascii=False)}")
            if "system_prompt" in agent:
                print(f"✓ 系统提示词: {agent['system_prompt']}")
            else:
                print("✗ 响应中没有 system_prompt 字段")
        else:
            print(f"✗ 未找到智能体 {agent_id}")
    else:
        print("✗ 获取智能体信息失败")

def test_edit_agent(agent_id: str):
    """测试编辑智能体"""
    print(f"\n=== 测试3: 编辑智能体 ===")
    
    edit_data = {
        "agent_name": "测试智能体（已编辑）",
        "system_prompt": "你是一个专业的技术顾问，说话风格严谨专业。"
    }
    
    response = requests.put(f"{BASE_URL}/api/admin/agents/{agent_id}", json=edit_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        print("✓ 智能体编辑成功")
        return True
    else:
        print("✗ 智能体编辑失败")
        return False

def test_verify_edit(agent_id: str):
    """验证编辑结果"""
    print(f"\n=== 测试4: 验证编辑结果 ===")
    
    response = requests.get(f"{BASE_URL}/api/admin/agents")
    
    if response.status_code == 200:
        data = response.json()
        agents = data.get("agents", [])
        agent = next((a for a in agents if a["agent_id"] == agent_id), None)
        
        if agent:
            print(f"智能体名称: {agent['agent_name']}")
            print(f"系统提示词: {agent.get('system_prompt', '无')}")
            
            if agent['agent_name'] == "测试智能体（已编辑）" and \
               agent.get('system_prompt') == "你是一个专业的技术顾问，说话风格严谨专业。":
                print("✓ 编辑结果验证成功")
                return True
            else:
                print("✗ 编辑结果不符合预期")
                return False
        else:
            print(f"✗ 未找到智能体 {agent_id}")
            return False
    else:
        print("✗ 获取智能体信息失败")
        return False

def cleanup(agent_id: str):
    """清理测试数据"""
    print(f"\n=== 清理测试数据 ===")
    response = requests.delete(f"{BASE_URL}/api/admin/agents/{agent_id}")
    if response.status_code == 200:
        print("✓ 测试数据清理成功")
    else:
        print(f"✗ 清理失败: {response.status_code}")

def main():
    print("开始测试智能体编辑功能...")
    
    auth_token = "test_token_123"
    
    # 测试1: 注册智能体
    agent_id = test_register_agent_with_system_prompt()
    if not agent_id:
        print("\n测试失败：无法注册智能体")
        return
    
    # 测试2: 获取智能体信息
    test_get_agent_info(agent_id)
    
    # 测试3: 编辑智能体
    if not test_edit_agent(agent_id):
        cleanup(agent_id)
        return
    
    # 测试4: 验证编辑结果
    success = test_verify_edit(agent_id)
    
    # 清理
    cleanup(agent_id)
    
    if success:
        print("\n" + "="*50)
        print("✓ 所有测试通过！")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("✗ 部分测试失败")
        print("="*50)

if __name__ == "__main__":
    main()
