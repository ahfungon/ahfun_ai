#!/usr/bin/env python3
"""
执行数据库迁移：添加 system_prompt 字段
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库URL
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("错误：未找到 DATABASE_URL 环境变量")
    exit(1)

print(f"连接数据库: {database_url.split('@')[1] if '@' in database_url else database_url}")

# 创建引擎
engine = create_engine(database_url)

# 执行迁移
try:
    with engine.connect() as conn:
        # 添加 system_prompt 字段
        conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS system_prompt TEXT"))
        
        # 添加注释
        conn.execute(text("COMMENT ON COLUMN agents.system_prompt IS 'System prompt for agent personality and speaking style'"))
        
        conn.commit()
        
    print("✓ 数据库迁移成功")
    print("  - 添加了 agents.system_prompt 字段")
    
except Exception as e:
    print(f"✗ 数据库迁移失败: {e}")
    exit(1)
