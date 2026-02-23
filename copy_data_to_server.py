#!/usr/bin/env python3
"""从本地数据库复制数据到服务器"""
import sys
from sqlalchemy import create_engine, text, inspect

# 本地和远程数据库连接
local_url = "postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat"
remote_url = "postgresql://dual_agent_user:dual_agent_pass@129.211.28.211:5432/dual_agent_chat"

def copy_data():
    """复制数据"""
    local_engine = create_engine(local_url)
    remote_engine = create_engine(remote_url)
    
    # 获取所有表
    inspector = inspect(local_engine)
    tables = inspector.get_table_names()
    
    print(f"Found {len(tables)} tables to copy")
    
    with local_engine.connect() as local_conn, remote_engine.connect() as remote_conn:
        for table in tables:
            print(f"\nCopying table: {table}")
            
            # 获取本地数据
            result = local_conn.execute(text(f"SELECT * FROM {table}"))
            rows = result.fetchall()
            columns = result.keys()
            
            if not rows:
                print(f"  No data in {table}")
                continue
            
            print(f"  Found {len(rows)} rows")
            
            # 插入到远程
            for i, row in enumerate(rows, 1):
                placeholders = ', '.join([f':{col}' for col in columns])
                cols = ', '.join(columns)
                sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
                
                # 转换为字典
                row_dict = dict(zip(columns, row))
                
                try:
                    remote_conn.execute(text(sql), row_dict)
                    if i % 10 == 0:
                        print(f"  Inserted {i}/{len(rows)} rows")
                except Exception as e:
                    print(f"  Error inserting row {i}: {e}")
                    continue
            
            remote_conn.commit()
            print(f"  ✓ Completed {table}")
    
    print("\n✓ Data copy completed!")

if __name__ == '__main__':
    try:
        copy_data()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
