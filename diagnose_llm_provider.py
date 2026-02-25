#!/usr/bin/env python3
"""
诊断 LLM 提供商配置
"""
import sys
sys.path.insert(0, '.')

from models.database import SessionLocal
from services.system_config_service import SystemConfigService

def diagnose():
    """诊断 LLM 提供商配置"""
    db = SessionLocal()
    
    try:
        config_service = SystemConfigService(db)
        
        print("=" * 60)
        print("LLM 提供商配置诊断")
        print("=" * 60)
        
        # 检查评分 LLM
        print("\n1. 消息评分 LLM 配置")
        print("-" * 60)
        scoring_provider = config_service.get_config_value('llm_provider_scoring', 'deepseek')
        print(f"提供商: {scoring_provider}")
        
        if scoring_provider == 'minimax':
            api_key = config_service.get_config_value('minimax_api_key', '')
            api_url = config_service.get_config_value('minimax_api_url', '')
            model = config_service.get_config_value('minimax_model', '')
            
            print(f"API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
            print(f"API URL: {api_url}")
            print(f"模型: {model}")
            
            if not api_key:
                print("❌ 警告: MiniMax API Key 未配置")
            else:
                print("✅ MiniMax API Key 已配置")
        else:
            api_key = config_service.get_config_value('deepseek_api_key', '')
            api_url = config_service.get_config_value('deepseek_api_url', '')
            model = config_service.get_config_value('deepseek_model', '')
            
            print(f"API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
            print(f"API URL: {api_url}")
            print(f"模型: {model}")
        
        # 检查总结 LLM
        print("\n2. 对话总结 LLM 配置")
        print("-" * 60)
        summary_provider = config_service.get_config_value('llm_provider_summary', 'deepseek')
        print(f"提供商: {summary_provider}")
        
        if summary_provider == 'minimax':
            api_key = config_service.get_config_value('minimax_api_key', '')
            api_url = config_service.get_config_value('minimax_api_url', '')
            model = config_service.get_config_value('minimax_model', '')
            
            print(f"API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
            print(f"API URL: {api_url}")
            print(f"模型: {model}")
            
            if not api_key:
                print("❌ 警告: MiniMax API Key 未配置")
            else:
                print("✅ MiniMax API Key 已配置")
        else:
            api_key = config_service.get_config_value('deepseek_api_key', '')
            api_url = config_service.get_config_value('deepseek_api_url', '')
            model = config_service.get_config_value('deepseek_model', '')
            
            print(f"API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
            print(f"API URL: {api_url}")
            print(f"模型: {model}")
        
        # 检查 Worker 状态
        print("\n3. Worker 状态检查")
        print("-" * 60)
        import subprocess
        result = subprocess.run(
            ["pgrep", "-f", "celery.*worker"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✅ Worker 正在运行 (PID: {', '.join(pids)})")
            print("\n⚠️ 如果刚修改了配置，需要重启 Worker:")
            print("   bash restart_worker_quick.sh")
        else:
            print("❌ Worker 未运行")
            print("\n启动 Worker:")
            print("   python quick_start.py")
        
        # 总结
        print("\n" + "=" * 60)
        print("诊断总结")
        print("=" * 60)
        
        if scoring_provider == 'minimax' or summary_provider == 'minimax':
            print("✅ 已配置使用 MiniMax")
            print("\n重要提示:")
            print("1. 确保 MiniMax API Key 已正确配置")
            print("2. 修改配置后必须重启 Worker")
            print("3. 重启命令: bash restart_worker_quick.sh")
        else:
            print("ℹ️ 当前使用 DeepSeek")
            print("\n如需切换到 MiniMax:")
            print("1. 访问系统配置页面")
            print("2. 修改 '消息评分 LLM 提供商' 和 '对话总结 LLM 提供商'")
            print("3. 保存配置")
            print("4. 重启 Worker: bash restart_worker_quick.sh")
        
    finally:
        db.close()


if __name__ == "__main__":
    diagnose()
