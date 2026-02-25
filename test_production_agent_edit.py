#!/usr/bin/env python3
"""
测试生产环境的智能体编辑功能
"""
import requests
import json

BASE_URL = "http://129.211.28.211:8080"

def test_register_agent_with_system_prompt():
    """测试注册带系统提示词的智能体"""
    print("\n=== 测试1: 注册带系统提示词的智能体 ===")
    
    agent_data = {
        "agent_name": "生产测试智能体",
        "auth_token": "prod_test_token_123",
        "system_prompt": "你是一个专业的技术顾问，说话风格严谨专业，善于用数据和案例支撑观点。"
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
                return True
            else:
                print("✗ 响应中没有 system_prompt 字段")
                return False
        else:
            print(f"✗ 未找到智能体 {agent_id}")
            return False
    else:
        print("✗ 获取智能体信息失败")
        return False

def test_edit_agent(agent_id: str):
    """测试编辑智能体"""
    print(f"\n=== 测试3: 编辑智能体 ===")
    
    edit_data = {
        "agent_name": "生产测试智能体（已编辑）",
        "system_prompt": "你是一个友好热情的客服代表，说话风格亲切温暖，善于倾听和解决问题。"
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
            
            if agent['agent_name'] == "生产测试智能体（已编辑）" and \
               agent.get('system_prompt') == "你是一个友好热情的客服代表，说话风格亲切温暖，善于倾听和解决问题。":
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

def main():
    print("开始测试生产环境的智能体编辑功能...")
    print(f"服务器: {BASE_URL}")
    
    # 测试1: 注册智能体
    agent_id = test_register_agent_with_system_prompt()
    if not agent_id:
        print("\n测试失败：无法注册智能体")
        return
    
    # 测试2: 获取智能体信息
    if not test_get_agent_info(agent_id):
        print("\n测试失败：无法获取智能体信息或缺少 system_prompt 字段")
        return
    
    # 测试3: 编辑智能体
    if not test_edit_agent(agent_id):
        return
    
    # 测试4: 验证编辑结果
    success = test_verify_edit(agent_id)
    
    if success:
        print("\n" + "="*50)
        print("✓ 生产环境所有测试通过！")
        print("="*50)
        print(f"\n测试智能体 ID: {agent_id}")
        print("可以在管理后台查看或删除此测试智能体")
    else:
        print("\n" + "="*50)
        print("✗ 部分测试失败")
        print("="*50)

if __name__ == "__main__":
    main()
