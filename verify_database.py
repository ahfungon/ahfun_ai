"""Script to verify database schema and tables."""
from sqlalchemy import inspect
from models.database import engine
from models import Topic, Message, Agent, SummaryJob, SummaryHistory, AuditLog


def verify_database():
    """Verify that all tables and indexes are created correctly."""
    inspector = inspect(engine)
    
    # Expected tables
    expected_tables = {
        'topics', 'messages', 'agents', 
        'summary_jobs', 'summary_history', 'audit_logs',
        'alembic_version'
    }
    
    # Get actual tables
    actual_tables = set(inspector.get_table_names())
    
    print("Database Verification")
    print("=" * 50)
    
    # Check tables
    print("\n1. Tables:")
    for table in expected_tables:
        if table in actual_tables:
            print(f"   ✓ {table}")
        else:
            print(f"   ✗ {table} (MISSING)")
    
    # Check indexes for topics table
    print("\n2. Topics Table Indexes:")
    topics_indexes = inspector.get_indexes('topics')
    expected_indexes = ['idx_topics_status', 'idx_topics_created_at', 'idx_topics_closing_timeout']
    for idx_name in expected_indexes:
        found = any(idx['name'] == idx_name for idx in topics_indexes)
        print(f"   {'✓' if found else '✗'} {idx_name}")
    
    # Check indexes for messages table
    print("\n3. Messages Table Indexes:")
    messages_indexes = inspector.get_indexes('messages')
    expected_indexes = ['idx_messages_topic_time']
    for idx_name in expected_indexes:
        found = any(idx['name'] == idx_name for idx in messages_indexes)
        print(f"   {'✓' if found else '✗'} {idx_name}")
    
    # Check indexes for summary_jobs table
    print("\n4. Summary Jobs Table Indexes:")
    jobs_indexes = inspector.get_indexes('summary_jobs')
    expected_indexes = ['idx_summary_jobs_topic', 'idx_summary_jobs_status_time']
    for idx_name in expected_indexes:
        found = any(idx['name'] == idx_name for idx in jobs_indexes)
        print(f"   {'✓' if found else '✗'} {idx_name}")
    
    # Check indexes for summary_history table
    print("\n5. Summary History Table Indexes:")
    history_indexes = inspector.get_indexes('summary_history')
    expected_indexes = ['idx_summary_history_topic_time']
    for idx_name in expected_indexes:
        found = any(idx['name'] == idx_name for idx in history_indexes)
        print(f"   {'✓' if found else '✗'} {idx_name}")
    
    # Check indexes for audit_logs table
    print("\n6. Audit Logs Table Indexes:")
    audit_indexes = inspector.get_indexes('audit_logs')
    expected_indexes = ['idx_audit_logs_topic_time', 'idx_audit_logs_agent_time', 'idx_audit_logs_operation_time']
    for idx_name in expected_indexes:
        found = any(idx['name'] == idx_name for idx in audit_indexes)
        print(f"   {'✓' if found else '✗'} {idx_name}")
    
    # Check columns for topics table
    print("\n7. Topics Table Columns:")
    topics_columns = inspector.get_columns('topics')
    expected_columns = [
        'id', 'title', 'status', 'summary', 'llm_suggestion', 'end_score',
        'token_count_since_summary', 'summary_threshold', 'last_summarized_message_id',
        'pending_summary_job', 'agent_a_wants_close', 'agent_b_wants_close',
        'closing_requested_by', 'closing_requested_at', 'created_at', 'updated_at'
    ]
    actual_columns = [col['name'] for col in topics_columns]
    for col_name in expected_columns:
        found = col_name in actual_columns
        print(f"   {'✓' if found else '✗'} {col_name}")
    
    print("\n" + "=" * 50)
    print("Database verification complete!")


if __name__ == "__main__":
    verify_database()
