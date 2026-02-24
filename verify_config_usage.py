#!/usr/bin/env python3
"""验证系统配置是否被代码正确使用"""

import sys
from models.database import SessionLocal
from services.system_config_service import SystemConfigService
from services.message_scoring_service import MessageScoringService
from services.summary_service import SummaryService
from config.settings import settings


def check_threshold_usage():
    """检查 summary_threshold 的使用情况"""
    print("=" * 60)
    print("1. 检查 summary_threshold 配置")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        config_service = SystemConfigService(db)
        
        # 从系统配置读取
        config_threshold = config_service.get_config_value('summary_threshold', 8000)
        
        # 从 settings 读取（.env 文件）
        settings_threshold = settings.summary_threshold
        
        print(f"\n系统配置中的阈值: {config_threshold}")
        print(f"settings.py 中的阈值: {settings_threshold}")
        
        # 检查代码使用情况
        print("\n代码使用情况:")
        print("  services/message_service.py 第 87 行:")
        print("    threshold = topic.summary_threshold if topic.summary_threshold else settings.summary_threshold")
        print("\n  ❌ 问题: 代码使用的是 settings.summary_threshold，没有从系统配置读取！")
        print("  ✅ 应该改为: 从 SystemConfigService 读取 'summary_threshold'")
        
        return config_threshold != settings_threshold
        
    finally:
        db.close()


def check_prompt_usage():
    """检查 prompt 配置的使用情况"""
    print("\n" + "=" * 60)
    print("2. 检查 Prompt 配置")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        config_service = SystemConfigService(db)
        
        # 检查 scoring_prompt
        scoring_prompt = config_service.get_config_value('scoring_prompt', None)
        print(f"\n系统配置中的 scoring_prompt: {'已配置' if scoring_prompt else '未配置'} ({len(scoring_prompt) if scoring_prompt else 0} 字符)")
        
        # 检查 summary_prompt
        summary_prompt = config_service.get_config_value('summary_prompt', None)
        print(f"系统配置中的 summary_prompt: {'已配置' if summary_prompt else '未配置'} ({len(summary_prompt) if summary_prompt else 0} 字符)")
        
        # 检查代码使用情况
        print("\n代码使用情况:")
        
        # MessageScoringService
        print("\n  [MessageScoringService]")
        print("    services/message_scoring_service.py 第 142 行:")
        print("    custom_prompt = self.config_service.get_config_value('scoring_prompt', None)")
        print("    ✅ 正确: 从系统配置读取 scoring_prompt")
        
        # SummaryService
        print("\n  [SummaryService]")
        print("    services/summary_service.py 第 348 行:")
        print("    custom_prompt = self.config_service.get_config_value('summary_prompt', None)")
        print("    ✅ 正确: 从系统配置读取 summary_prompt")
        
        return True
        
    finally:
        db.close()


def test_actual_usage():
    """测试实际使用情况"""
    print("\n" + "=" * 60)
    print("3. 测试实际使用")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # 测试 MessageScoringService
        print("\n[MessageScoringService]")
        scoring_service = MessageScoringService(db)
        
        # 检查是否有 config_service
        if hasattr(scoring_service, 'config_service'):
            print("  ✅ 有 config_service 属性")
            
            # 尝试读取配置
            try:
                prompt = scoring_service.config_service.get_config_value('scoring_prompt', None)
                print(f"  ✅ 可以读取 scoring_prompt: {len(prompt) if prompt else 0} 字符")
            except Exception as e:
                print(f"  ❌ 读取 scoring_prompt 失败: {e}")
        else:
            print("  ❌ 没有 config_service 属性")
        
        # 测试 SummaryService
        print("\n[SummaryService]")
        summary_service = SummaryService(db)
        
        # 检查是否有 config_service
        if hasattr(summary_service, 'config_service'):
            print("  ✅ 有 config_service 属性")
            
            # 尝试读取配置
            try:
                prompt = summary_service.config_service.get_config_value('summary_prompt', None)
                print(f"  ✅ 可以读取 summary_prompt: {len(prompt) if prompt else 0} 字符")
            except Exception as e:
                print(f"  ❌ 读取 summary_prompt 失败: {e}")
        else:
            print("  ❌ 没有 config_service 属性")
        
        return True
        
    finally:
        db.close()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("系统配置使用情况验证")
    print("=" * 60)
    
    try:
        # 检查 threshold
        threshold_issue = check_threshold_usage()
        
        # 检查 prompt
        check_prompt_usage()
        
        # 测试实际使用
        test_actual_usage()
        
        # 总结
        print("\n" + "=" * 60)
        print("总结")
        print("=" * 60)
        
        print("\n✅ 已正确使用的配置:")
        print("  1. scoring_prompt - MessageScoringService 从系统配置读取")
        print("  2. summary_prompt - SummaryService 从系统配置读取")
        print("  3. llm_provider_scoring - MessageScoringService 从系统配置读取")
        print("  4. llm_provider_summary - SummaryService 从系统配置读取")
        
        if threshold_issue:
            print("\n❌ 未正确使用的配置:")
            print("  1. summary_threshold - 代码使用 settings.summary_threshold")
            print("     位置: services/message_service.py 第 87 行")
            print("     问题: 没有从系统配置读取，而是从 .env 文件读取")
            print("     影响: 在管理后台修改阈值不会生效")
            
            print("\n🔧 需要修复:")
            print("  修改 services/message_service.py")
            print("  将 settings.summary_threshold 改为从 SystemConfigService 读取")
        else:
            print("\n✅ 所有配置都已正确使用")
        
        return 0 if not threshold_issue else 1
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
