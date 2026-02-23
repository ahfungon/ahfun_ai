#!/usr/bin/env python3
"""
验证 LLM 配置脚本

检查模拟器的 LLM 配置是否正确
"""

import os
import sys
import yaml
from pathlib import Path

def main():
    print("=" * 80)
    print("LLM 配置验证")
    print("=" * 80)
    
    # 1. 检查配置文件
    print("\n1️⃣ 检查配置文件 (config.yaml)")
    print("-" * 80)
    
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("❌ 配置文件不存在")
        return 1
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    llm_config = config.get("llm", {})
    print(f"✓ API URL: {llm_config.get('api_url', 'N/A')}")
    print(f"✓ Model: {llm_config.get('model', 'N/A')}")
    
    config_api_key = llm_config.get('api_key', '')
    if config_api_key:
        print(f"✓ API Key (config): 已设置 ({config_api_key[:10]}...)")
    else:
        print(f"✓ API Key (config): 未设置（将从环境变量读取）")
    
    # 2. 检查环境变量
    print("\n2️⃣ 检查环境变量")
    print("-" * 80)
    
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if deepseek_key:
        print(f"✓ DEEPSEEK_API_KEY: 已设置 ({deepseek_key[:10]}...)")
    else:
        print(f"⚠ DEEPSEEK_API_KEY: 未设置")
    
    if openai_key:
        print(f"✓ OPENAI_API_KEY: 已设置 ({openai_key[:10]}...)")
    else:
        print(f"⚠ OPENAI_API_KEY: 未设置")
    
    # 3. 确定最终使用的配置
    print("\n3️⃣ 最终配置（按优先级）")
    print("-" * 80)
    
    if deepseek_key:
        print("✅ 将使用: DEEPSEEK_API_KEY 环境变量")
        print(f"   API URL: https://api.deepseek.com/v1")
        print(f"   Model: deepseek-chat")
        print(f"   优先级: 最高 (1)")
        final_config = "deepseek_env"
    elif openai_key:
        print("⚠️  将使用: OPENAI_API_KEY 环境变量")
        print(f"   API URL: https://api.openai.com/v1")
        print(f"   Model: gpt-3.5-turbo")
        print(f"   优先级: 中 (2)")
        final_config = "openai_env"
    elif config_api_key:
        print("⚠️  将使用: config.yaml 中的 api_key")
        print(f"   API URL: {llm_config.get('api_url')}")
        print(f"   Model: {llm_config.get('model')}")
        print(f"   优先级: 低 (3)")
        final_config = "config_file"
    else:
        print("❌ 未找到任何 API 密钥")
        print("   模拟器将使用预设回复（不调用 LLM）")
        final_config = "none"
    
    # 4. 检查 .env 文件
    print("\n4️⃣ 检查 .env 文件（评分系统配置）")
    print("-" * 80)
    
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        print("✓ .env 文件存在")
        with open(env_path, 'r') as f:
            env_content = f.read()
            if 'DEEPSEEK_API_KEY' in env_content:
                print("✓ .env 包含 DEEPSEEK_API_KEY")
                print("\n  提示：可以使用以下命令加载 .env 文件：")
                print("  $ source .env")
                print("  $ export DEEPSEEK_API_KEY")
            else:
                print("⚠ .env 不包含 DEEPSEEK_API_KEY")
    else:
        print("⚠ .env 文件不存在")
    
    # 5. 给出建议
    print("\n5️⃣ 配置建议")
    print("-" * 80)
    
    if final_config == "deepseek_env":
        print("✅ 配置完美！")
        print("   - 使用 DeepSeek API（与评分系统一致）")
        print("   - 通过环境变量配置（安全）")
        print("\n   运行命令：")
        print("   $ python enhanced_simulator.py --use-llm --rounds 5")
    elif final_config == "openai_env":
        print("⚠️  配置可用，但建议使用 DeepSeek")
        print("   - 当前使用 OpenAI API")
        print("   - 评分系统使用 DeepSeek API")
        print("   - 建议统一使用 DeepSeek")
        print("\n   修改方法：")
        print("   $ export DEEPSEEK_API_KEY='your-deepseek-key'")
        print("   $ unset OPENAI_API_KEY")
    elif final_config == "config_file":
        print("⚠️  配置可用，但不推荐")
        print("   - API 密钥暴露在配置文件中")
        print("   - 建议使用环境变量")
        print("\n   修改方法：")
        print("   $ export DEEPSEEK_API_KEY='your-deepseek-key'")
        print("   $ # 然后清空 config.yaml 中的 api_key")
    else:
        print("❌ 未配置 LLM")
        print("   - 模拟器将使用预设回复")
        print("   - 如需使用 LLM，请配置 API 密钥")
        print("\n   配置方法：")
        print("   $ export DEEPSEEK_API_KEY='your-deepseek-key'")
        print("   $ python enhanced_simulator.py --use-llm")
    
    # 6. 总结
    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)
    
    if final_config in ["deepseek_env", "openai_env", "config_file"]:
        print("\n✅ 可以使用 --use-llm 参数运行模拟器")
        return 0
    else:
        print("\n⚠️  未配置 LLM，只能使用预设回复模式")
        return 1

if __name__ == "__main__":
    sys.exit(main())
