#!/usr/bin/env python3
"""Initialize system configuration table and default values."""

import sys
from sqlalchemy import text
from models.database import get_db, engine
from services.system_config_service import SystemConfigService


def create_table():
    """Create system_configs table if not exists."""
    print("Creating system_configs table...")
    
    with open("migrations/create_system_config_table.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    
    # Split into main DDL and comments
    statements = []
    for statement in sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            statements.append(statement)
    
    # Execute DDL statements first
    with engine.begin() as conn:
        for statement in statements:
            if not statement.startswith('COMMENT'):
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    if "already exists" not in str(e):
                        print(f"Warning: {e}")
    
    # Execute COMMENT statements separately
    with engine.begin() as conn:
        for statement in statements:
            if statement.startswith('COMMENT'):
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    print(f"Warning: {e}")
    
    print("✅ Table created successfully")


def initialize_defaults():
    """Initialize default configuration values."""
    print("\nInitializing default configurations...")
    
    db = next(get_db())
    try:
        config_service = SystemConfigService(db)
        config_service.initialize_defaults()
        
        # Get all configs to display
        configs = config_service.get_all_configs()
        
        print(f"✅ Initialized {len(configs)} configurations:")
        print()
        
        # Group by category
        by_category = {}
        for config in configs:
            if config.category not in by_category:
                by_category[config.category] = []
            by_category[config.category].append(config)
        
        for category, cat_configs in by_category.items():
            print(f"📁 {category.upper()}")
            for config in cat_configs:
                value_preview = config.value[:50] + "..." if len(config.value) > 50 else config.value
                if config.config_type == "password" and config.value:
                    value_preview = "••••••••"
                print(f"  - {config.display_name}: {value_preview}")
            print()
        
    finally:
        db.close()


def main():
    """Main function."""
    print("=" * 60)
    print("系统配置初始化")
    print("=" * 60)
    print()
    
    try:
        # Create table
        create_table()
        
        # Initialize defaults
        initialize_defaults()
        
        print("=" * 60)
        print("✅ 初始化完成！")
        print()
        print("访问管理后台查看配置：")
        print("  http://localhost:8080/system-config.html")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
