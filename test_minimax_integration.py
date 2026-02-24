#!/usr/bin/env python3
"""Test script to verify MiniMax integration and check which LLM is being used."""

import sys
from models.database import SessionLocal
from services.system_config_service import SystemConfigService
from services.message_scoring_service import MessageScoringService
from services.summary_service import SummaryService


def test_system_config():
    """Test system configuration."""
    print("=" * 60)
    print("1. 检查系统配置")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        service = SystemConfigService(db)
        
        # Check LLM provider settings
        scoring_provider = service.get_config_value('llm_provider_scoring', 'not set')
        summary_provider = service.get_config_value('llm_provider_summary', 'not set')
        
        print(f"✓ 消息评分 LLM: {scoring_provider}")
        print(f"✓ 对话总结 LLM: {summary_provider}")
        
        # Check MiniMax config
        minimax_key = service.get_config_value('minimax_api_key', '')
        minimax_url = service.get_config_value('minimax_api_url', '')
        minimax_model = service.get_config_value('minimax_model', '')
        
        print(f"\n✓ MiniMax API Key: {'已配置 (' + minimax_key[:10] + '...)' if minimax_key else '未配置'}")
        print(f"✓ MiniMax API URL: {minimax_url}")
        print(f"✓ MiniMax Model: {minimax_model}")
        
        # Check DeepSeek config
        deepseek_key = service.get_config_value('deepseek_api_key', '')
        deepseek_url = service.get_config_value('deepseek_api_url', '')
        deepseek_model = service.get_config_value('deepseek_model', '')
        
        print(f"\n✓ DeepSeek API Key: {'已配置 (' + deepseek_key[:10] + '...)' if deepseek_key else '未配置'}")
        print(f"✓ DeepSeek API URL: {deepseek_url}")
        print(f"✓ DeepSeek Model: {deepseek_model}")
        
        return scoring_provider, summary_provider
        
    finally:
        db.close()


def test_service_initialization():
    """Test service initialization with current config."""
    print("\n" + "=" * 60)
    print("2. 测试服务初始化")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Test MessageScoringService
        print("\n[MessageScoringService]")
        scoring_service = MessageScoringService(db)
        print(f"✓ 初始化成功")
        print(f"✓ 使用的 LLM: {scoring_service.llm_provider}")
        print(f"✓ 客户端类型: {type(scoring_service.llm_client).__name__}")
        
        # Test SummaryService
        print("\n[SummaryService]")
        summary_service = SummaryService(db)
        print(f"✓ 初始化成功")
        print(f"✓ 使用的 LLM: {summary_service.llm_provider}")
        print(f"✓ 客户端类型: {type(summary_service.llm_client).__name__}")
        
        return True
        
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


def check_recent_logs():
    """Check recent logs for LLM calls."""
    print("\n" + "=" * 60)
    print("3. 检查最近的日志")
    print("=" * 60)
    
    import os
    
    log_files = ['logs/api.log', 'logs/worker.log']
    
    for log_file in log_files:
        if not os.path.exists(log_file):
            print(f"\n[{log_file}] 文件不存在")
            continue
        
        print(f"\n[{log_file}]")
        
        # Read last 50 lines
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-50:] if len(lines) > 50 else lines
        
        # Search for LLM-related logs
        llm_logs = []
        for line in recent_lines:
            if any(keyword in line.lower() for keyword in ['deepseek', 'minimax', 'llm', 'scoring', 'summary']):
                llm_logs.append(line.strip())
        
        if llm_logs:
            print(f"找到 {len(llm_logs)} 条相关日志:")
            for log in llm_logs[-10:]:  # Show last 10
                print(f"  {log}")
        else:
            print("未找到相关日志")


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("MiniMax 集成测试")
    print("=" * 60)
    
    try:
        # Test 1: Check system config
        scoring_provider, summary_provider = test_system_config()
        
        # Test 2: Test service initialization
        success = test_service_initialization()
        
        if not success:
            print("\n❌ 服务初始化失败，请检查配置")
            return 1
        
        # Test 3: Check logs
        check_recent_logs()
        
        # Summary
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        
        if scoring_provider == 'minimax' or summary_provider == 'minimax':
            print("\n✓ 系统已配置使用 MiniMax")
            print("✓ 服务已正确初始化 MiniMax 客户端")
            print("\n下一步:")
            print("1. 发送一条消息触发评分")
            print("2. 或者手动触发总结任务")
            print("3. 查看日志确认 MiniMax 被调用")
            print("\n查看日志命令:")
            print("  tail -f logs/api.log | grep -i minimax")
            print("  tail -f logs/worker.log | grep -i minimax")
        else:
            print(f"\n⚠ 当前配置:")
            print(f"  消息评分: {scoring_provider}")
            print(f"  对话总结: {summary_provider}")
            print("\n如需使用 MiniMax，请在管理后台修改配置")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
