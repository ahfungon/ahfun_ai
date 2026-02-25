#!/usr/bin/env python3
"""
修复 MiniMax API URL
"""
import sys
sys.path.insert(0, '.')

from models.database import SessionLocal
from services.system_config_service import SystemConfigService

def fix_url():
    """修复 MiniMax API URL"""
    db = SessionLocal()
    
    try:
        config_service = SystemConfigService(db)
        
        print("=" * 60)
        print("修复 MiniMax API URL")
        print("=" * 60)
        
        # 检查当前 URL
        current_url = config_service.get_config_value('minimax_api_url', '')
        print(f"\n当前 URL: {current_url}")
        
        # 正确的 URL（旧平台）
        correct_url = "https://api.minimax.chat/v1"
        
        if current_url == correct_url:
            print("✅ URL 已经是正确的")
        else:
            print(f"\n修复为: {correct_url}")
            print("原因: 你的 API Key 是旧平台格式，只能在旧域名使用")
            
            # 更新 URL
            config_service.update_config('minimax_api_url', correct_url)
            print("\n✅ URL 已更新")
            
            print("\n⚠️ 重要: 需要重启 Worker 才能生效")
            print("重启命令: bash restart_worker_quick.sh")
        
        print("\n" + "=" * 60)
        
    finally:
        db.close()


if __name__ == "__main__":
    fix_url()
