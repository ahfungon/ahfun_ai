#!/usr/bin/env python3
"""
Fix prompt escaping in database.

This script updates the scoring_prompt and summary_prompt in the database
to escape JSON example curly braces ({{ and }}) so they don't interfere
with Python's .format() method.
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.system_config import SystemConfig
from config.settings import settings

def fix_prompt_escaping():
    """Fix prompt escaping in database."""
    # Create database connection
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Fix scoring_prompt
        scoring_config = db.query(SystemConfig).filter(
            SystemConfig.key == 'scoring_prompt'
        ).first()
        
        if scoring_config:
            old_value = scoring_config.value
            # Check if it needs fixing (contains unescaped JSON example)
            if '"relevance_score":' in old_value and '{{' not in old_value:
                print("🔧 Fixing scoring_prompt...")
                # Replace unescaped braces in JSON example
                new_value = old_value.replace(
                    '{\n    "relevance_score"',
                    '{{\n    "relevance_score"'
                ).replace(
                    '    "evaluation_comment": "发言紧扣主题，观点独特，逻辑清晰，有效推动了对话发展。"\n}',
                    '    "evaluation_comment": "发言紧扣主题，观点独特，逻辑清晰，有效推动了对话发展。"\n}}'
                )
                scoring_config.value = new_value
                print("✅ scoring_prompt fixed")
            else:
                print("✓ scoring_prompt already correct")
        else:
            print("⚠️  scoring_prompt not found in database")
        
        # Fix summary_prompt
        summary_config = db.query(SystemConfig).filter(
            SystemConfig.key == 'summary_prompt'
        ).first()
        
        if summary_config:
            old_value = summary_config.value
            # Check if it needs fixing (contains unescaped JSON example)
            if '"summary":' in old_value and '{{' not in old_value:
                print("🔧 Fixing summary_prompt...")
                # Replace unescaped braces in JSON example
                new_value = old_value.replace(
                    '{\n    "summary"',
                    '{{\n    "summary"'
                ).replace(
                    '    "end_score": 75\n}',
                    '    "end_score": 75\n}}'
                )
                summary_config.value = new_value
                print("✅ summary_prompt fixed")
            else:
                print("✓ summary_prompt already correct")
        else:
            print("⚠️  summary_prompt not found in database")
        
        # Commit changes
        db.commit()
        print("\n✅ Database prompts updated successfully!")
        print("\n📝 Next steps:")
        print("1. Restart API server: Ctrl+C and restart main.py")
        print("2. Restart Worker: bash restart_worker_quick.sh")
        print("3. Test scoring with: python3 check_recent_scoring.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    fix_prompt_escaping()
