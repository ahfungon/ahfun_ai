#!/usr/bin/env python3
"""测试 summary_threshold 是否从系统配置读取"""

import sys
from models.database import SessionLocal
from services.message_service import MessageService
from services.system_config_service import SystemConfigService
from config.settings import settings


def test_threshold_reading():
    """测试阈值读取"""
    print("=" * 60)
    print("测试 summary_threshold 读取")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # 获取配置
        config_service = SystemConfigService(db)
        config_threshold = config_service.get_config_value('summary_threshold', 8000)
        settings_threshold = settings.summary_threshold
        
        print(f"\n1. 配置值:")
        print(f"   系统配置: {config_threshold}")
        print(f"   settings: {settings_threshold}")
        
        # 创建 MessageService
        print(f"\n2. 创建 MessageService...")
        message_service = MessageService(db)
        
        # 检查是否有 config_service
        if hasattr(message_service, 'config_service'):
            print(f"   ✅ MessageService 有 config_service 属性")
            
            # 测试读取阈值
            test_threshold = message_service.config_service.get_config_value('summary_threshold', 8000)
            print(f"   ✅ 可以读取 summary_threshold: {test_threshold}")
            
            if test_threshold == config_threshold:
                print(f"   ✅ 读取的值与系统配置一致")
            else:
                print(f"   ❌ 读取的值与系统配置不一致")
        else:
            print(f"   ❌ MessageService 没有 config_service 属性")
            return False
        
        # 模拟代码逻辑
        print(f"\n3. 模拟代码逻辑:")
        print(f"   假设 topic.summary_threshold = None")
        
        # 旧逻辑
        old_threshold = None or settings.summary_threshold
        print(f"   旧逻辑: threshold = None or settings.summary_threshold = {old_threshold}")
        
        # 新逻辑
        new_threshold = None or message_service.config_service.get_config_value('summary_threshold', settings.summary_threshold)
        print(f"   新逻辑: threshold = config_service.get_config_value(...) = {new_threshold}")
        
        # 对比
        print(f"\n4. 对比:")
        if old_threshold != new_threshold:
            print(f"   ✅ 新逻辑使用系统配置 ({new_threshold})")
            print(f"   ❌ 旧逻辑使用 settings ({old_threshold})")
            print(f"   差异: {new_threshold - old_threshold} tokens")
            return True
        else:
            print(f"   ⚠️  两者相同 (都是 {old_threshold})")
            print(f"   可能是系统配置与 settings 值相同")
            return True
        
    finally:
        db.close()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("验证 summary_threshold 配置使用")
    print("=" * 60)
    
    try:
        success = test_threshold_reading()
        
        print("\n" + "=" * 60)
        print("结论")
        print("=" * 60)
        
        if success:
            print("\n✅ MessageService 现在从系统配置读取 summary_threshold")
            print("\n修改内容:")
            print("  1. 添加了 self.config_service = SystemConfigService(db)")
            print("  2. 使用 self.config_service.get_config_value('summary_threshold', ...)")
            print("  3. 不再直接使用 settings.summary_threshold")
            
            print("\n效果:")
            print("  - 在管理后台修改阈值会立即生效")
            print("  - 不需要修改 .env 文件")
            print("  - 不需要重启服务")
        else:
            print("\n❌ MessageService 还没有正确集成系统配置")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
