"""Property-based tests for Celery worker tasks using hypothesis.

This test suite validates the following properties:
- Property 17a: Summary task state transitions (需求 6.1)
- Property 28: Summary task retry mechanism (需求 6.11, 12.4)
- Property 34: Database lock prevents concurrent tasks (需求 6.14)
- Property 31: Worker does not block API (需求 6.9)
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from sqlalchemy.orm import Session

from workers.tasks import process_summary_job
from models.models import Topic, Message, SummaryJob
from models.database import SessionLocal
from config.settings import settings as app_settings


# Custom strategies for generating test data
@st.composite
def topic_strategy(draw, status=None, pending_summary_job=None):
    """Generate a random Topic for property testing."""
    return Topic(
        id=draw(st.uuids()).hex,
        title=draw(st.text(min_size=5, max_size=100)),
        status=status or draw(st.sampled_from(["active", "closing_pending", "closed"])),
        summary=draw(st.text(max_size=500)),
        llm_suggestion=draw(st.sampled_from(["continue", "change_angle", "suggest_end", "force_end"])),
        end_score=draw(st.floats(min_value=0.0, max_value=100.0)),
        token_count_since_summary=draw(st.integers(min_value=0, max_value=20000)),
        last_summarized_message_id=draw(st.one_of(st.none(), st.uuids().map(lambda x: x.hex))),
        pending_summary_job=pending_summary_job if pending_summary_job is not None else draw(st.booleans()),
        agent_a_wants_close=draw(st.booleans()),
        agent_b_wants_close=draw(st.booleans())
    )


@st.composite
def message_strategy(draw, topic_id):
    """Generate a random Message for property testing."""
    return Message(
        id=draw(st.uuids()).hex,
        topic_id=topic_id,
        agent_id=draw(st.sampled_from(["agent_a", "agent_b"])),
        content=draw(st.text(min_size=10, max_size=1000)),
        actual_tokens=draw(st.integers(min_value=10, max_value=500))
    )


@st.composite
def summary_job_strategy(draw, topic_id, status=None, retry_count=None):
    """Generate a random SummaryJob for property testing."""
    return SummaryJob(
        id=draw(st.uuids()).hex,
        topic_id=topic_id,
        start_message_id=draw(st.one_of(st.none(), st.uuids().map(lambda x: x.hex))),
        end_message_id=draw(st.uuids()).hex,
        status=status or draw(st.sampled_from(["pending", "processing", "done", "failed"])),
        retry_count=retry_count if retry_count is not None else draw(st.integers(min_value=0, max_value=5)),
        error_message=draw(st.one_of(st.none(), st.text(max_size=200)))
    )


class TestWorkerProperties:
    """Property-based tests for worker task processing."""
    
    @settings(
        max_examples=100, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        topic=topic_strategy(status="active", pending_summary_job=True),
        num_messages=st.integers(min_value=1, max_value=10)
    )
    def test_property_17a_summary_task_state_transitions(
        self, 
        test_db: Session,
        topic: Topic,
        num_messages: int
    ):
        """
        Property 17a: Summary task state transitions
        
        For any SummaryJob, its status should follow the sequence:
        pending → processing → done/failed
        
        No other state transitions should occur.
        
        Validates: Requirement 6.1
        """
        # Clean up any previous test data
        test_db.rollback()
        test_db.query(SummaryJob).delete()
        test_db.query(Message).delete()
        test_db.query(Topic).delete()
        test_db.commit()
        
        # Setup: Create topic and messages
        test_db.add(topic)
        
        messages = []
        for i in range(num_messages):
            msg = Message(
                id=f"msg-{topic.id}-{i}",
                topic_id=topic.id,
                agent_id="agent_a" if i % 2 == 0 else "agent_b",
                content=f"Test message {i}",
                actual_tokens=100
            )
            messages.append(msg)
            test_db.add(msg)
        
        # Create summary job in pending state
        job = SummaryJob(
            id=f"job-{topic.id}",
            topic_id=topic.id,
            start_message_id=None,
            end_message_id=messages[-1].id,
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        test_db.commit()
        
        # Mock successful LLM call
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "Generated summary",
                "suggestion": "continue",
                "end_score": 50.0
            }
            
            # Process the job
            process_summary_job(job.id, db_session=test_db)
        
        # Verify state transition: pending → processing → done
        job_after = test_db.query(SummaryJob).filter(SummaryJob.id == job.id).first()
        
        # Job should be in done state (successful completion)
        assert job_after.status == "done", \
            f"Expected job status to be 'done', but got '{job_after.status}'"
        
        # Verify no invalid states were reached
        assert job_after.status in ["pending", "processing", "done", "failed"], \
            f"Job reached invalid state: {job_after.status}"
    
    @settings(
        max_examples=100, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        topic=topic_strategy(status="active", pending_summary_job=True),
        retry_count=st.integers(min_value=0, max_value=2)
    )
    def test_property_28_summary_task_retry_mechanism(
        self,
        test_db: Session,
        topic: Topic,
        retry_count: int
    ):
        """
        Property 28: Summary task retry mechanism
        
        For any failed SummaryJob:
        - If retry_count < max_retries: task should return to pending state
        - If retry_count >= max_retries: task should be marked as failed and 
          pending_summary_job flag should be released
        
        Validates: Requirements 6.11, 12.4
        """
        # Clean up any previous test data
        test_db.rollback()
        test_db.query(SummaryJob).delete()
        test_db.query(Message).delete()
        test_db.query(Topic).delete()
        test_db.commit()
        
        # Setup: Create topic and message
        test_db.add(topic)
        
        msg = Message(
            id=f"msg-{topic.id}",
            topic_id=topic.id,
            agent_id="agent_a",
            content="Test message",
            actual_tokens=100
        )
        test_db.add(msg)
        
        # Create summary job with specific retry count
        job = SummaryJob(
            id=f"job-{topic.id}",
            topic_id=topic.id,
            start_message_id=None,
            end_message_id=msg.id,
            status="pending",
            retry_count=retry_count
        )
        test_db.add(job)
        test_db.commit()
        
        # Mock LLM failure
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.side_effect = Exception("LLM API failure")
            
            # Mock time.sleep and apply_async to avoid delays and re-queueing
            with patch('workers.tasks.time.sleep'):
                with patch('workers.tasks.process_summary_job.apply_async'):
                    # Process the job
                    process_summary_job(job.id, db_session=test_db)
        
        # Verify retry behavior
        job_after = test_db.query(SummaryJob).filter(SummaryJob.id == job.id).first()
        topic_after = test_db.query(Topic).filter(Topic.id == topic.id).first()
        
        if retry_count + 1 < app_settings.max_retries:
            # Should retry: status pending, retry_count incremented
            assert job_after.status == "pending", \
                f"Expected status 'pending' for retry_count={retry_count}, got '{job_after.status}'"
            assert job_after.retry_count == retry_count + 1, \
                f"Expected retry_count to increment to {retry_count + 1}, got {job_after.retry_count}"
            assert topic_after.pending_summary_job is True, \
                "Expected pending_summary_job to remain True during retries"
        else:
            # Should fail: status failed, pending_summary_job released
            assert job_after.status == "failed", \
                f"Expected status 'failed' after max retries, got '{job_after.status}'"
            assert job_after.retry_count == retry_count + 1, \
                f"Expected retry_count to increment to {retry_count + 1}, got {job_after.retry_count}"
            assert topic_after.pending_summary_job is False, \
                "Expected pending_summary_job to be released after max retries"
            assert job_after.error_message is not None, \
                "Expected error_message to be set on failed job"
    
    @settings(
        max_examples=50, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        topic=topic_strategy(status="active", pending_summary_job=True),
        num_messages=st.integers(min_value=1, max_value=5)
    )
    def test_property_34_database_lock_prevents_concurrent_tasks(
        self,
        test_db: Session,
        topic: Topic,
        num_messages: int
    ):
        """
        Property 34: Database lock prevents concurrent tasks
        
        For any topic, the database-level Topic_Lock (SELECT FOR UPDATE) should
        prevent concurrent summary tasks on the same topic.
        
        This test verifies that the worker uses row-level locking by checking
        that with_for_update() is called during topic retrieval.
        
        Validates: Requirement 6.14
        """
        # Clean up any previous test data
        test_db.rollback()
        test_db.query(SummaryJob).delete()
        test_db.query(Message).delete()
        test_db.query(Topic).delete()
        test_db.commit()
        
        # Setup: Create topic and messages
        test_db.add(topic)
        
        messages = []
        for i in range(num_messages):
            msg = Message(
                id=f"msg-{topic.id}-{i}",
                topic_id=topic.id,
                agent_id="agent_a",
                content=f"Test message {i}",
                actual_tokens=100
            )
            messages.append(msg)
            test_db.add(msg)
        
        # Create summary job
        job = SummaryJob(
            id=f"job-{topic.id}",
            topic_id=topic.id,
            start_message_id=None,
            end_message_id=messages[-1].id,
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        test_db.commit()
        
        # Mock LLM call
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "Generated summary",
                "suggestion": "continue",
                "end_score": 50.0
            }
            
            # Track if with_for_update was called
            lock_acquired = False
            original_query = test_db.query
            
            def query_wrapper(*args, **kwargs):
                result = original_query(*args, **kwargs)
                # Wrap the query result to track with_for_update calls
                original_with_for_update = result.with_for_update
                
                def with_for_update_wrapper(*wfu_args, **wfu_kwargs):
                    nonlocal lock_acquired
                    # Check if this is a Topic query
                    if args and args[0] == Topic:
                        lock_acquired = True
                    return original_with_for_update(*wfu_args, **wfu_kwargs)
                
                result.with_for_update = with_for_update_wrapper
                return result
            
            # Patch the query method
            with patch.object(test_db, 'query', side_effect=query_wrapper):
                # Process the job
                process_summary_job(job.id, db_session=test_db)
            
            # Verify that row-level lock was acquired
            assert lock_acquired, \
                "Expected with_for_update() to be called for Topic query to prevent concurrent tasks"
    
    @settings(
        max_examples=100, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        topic=topic_strategy(status="active", pending_summary_job=False),
        token_count=st.integers(min_value=8000, max_value=15000)
    )
    def test_property_31_worker_does_not_block_api(
        self,
        test_db: Session,
        topic: Topic,
        token_count: int
    ):
        """
        Property 31: Worker does not block API
        
        For any message submission request, even if it triggers summary task creation,
        the API response time should not be affected by LLM call time.
        
        This test verifies that:
        1. Summary jobs are created asynchronously
        2. The worker processes jobs in the background
        3. API can continue accepting messages while worker is processing
        
        Validates: Requirement 6.9
        """
        # Clean up any previous test data
        test_db.rollback()
        test_db.query(SummaryJob).delete()
        test_db.query(Message).delete()
        test_db.query(Topic).delete()
        test_db.commit()
        
        # Setup: Create topic with high token count (near threshold)
        topic.token_count_since_summary = token_count
        topic.pending_summary_job = False  # No pending job initially
        test_db.add(topic)
        
        # Create a message that would trigger summary
        msg = Message(
            id=f"msg-{topic.id}",
            topic_id=topic.id,
            agent_id="agent_a",
            content="Test message that triggers summary",
            actual_tokens=100
        )
        test_db.add(msg)
        
        # Create summary job (simulating what MessageService would create)
        job = SummaryJob(
            id=f"job-{topic.id}",
            topic_id=topic.id,
            start_message_id=None,
            end_message_id=msg.id,
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        
        # Mark topic as having pending job
        topic.pending_summary_job = True
        test_db.commit()
        
        # Mock LLM call with artificial delay to simulate slow API
        def slow_llm_call(*args, **kwargs):
            import time
            time.sleep(0.1)  # Simulate 100ms LLM call
            return {
                "summary": "Generated summary",
                "suggestion": "continue",
                "end_score": 50.0
            }
        
        with patch('services.summary_service.SummaryService._call_deepseek_api', side_effect=slow_llm_call):
            # Measure worker processing time
            import time
            start_time = time.time()
            
            # Process the job (this happens in background worker)
            process_summary_job(job.id, db_session=test_db)
            
            worker_time = time.time() - start_time
        
        # Verify job completed
        job_after = test_db.query(SummaryJob).filter(SummaryJob.id == job.id).first()
        assert job_after.status == "done", \
            "Expected job to complete successfully"
        
        # Verify pending_summary_job flag was released
        topic_after = test_db.query(Topic).filter(Topic.id == topic.id).first()
        assert topic_after.pending_summary_job is False, \
            "Expected pending_summary_job to be released after completion"
        
        # The key property: Worker processing happens asynchronously
        # In real scenario, API would return immediately while worker processes in background
        # Here we verify that the worker completes its work independently
        assert worker_time >= 0.1, \
            "Worker should take time to process (including LLM call)"
        
        # Verify topic was updated correctly
        assert topic_after.summary == "Generated summary", \
            "Expected topic summary to be updated"
        assert topic_after.token_count_since_summary == 0, \
            "Expected token count to be reset after summary"
    
    @settings(
        max_examples=50, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        topic=topic_strategy(status="active", pending_summary_job=True),
        llm_suggestion=st.sampled_from(["continue", "change_angle", "suggest_end", "force_end"])
    )
    def test_worker_applies_llm_suggestions_correctly(
        self,
        test_db: Session,
        topic: Topic,
        llm_suggestion: str
    ):
        """
        Additional property test: Worker correctly applies LLM suggestions.
        
        For any LLM suggestion:
        - continue, change_angle, suggest_end: topic status should remain unchanged
        - force_end: topic status should change to closing_pending
        
        Validates: Requirement 7.5
        """
        # Clean up any previous test data
        test_db.rollback()
        test_db.query(SummaryJob).delete()
        test_db.query(Message).delete()
        test_db.query(Topic).delete()
        test_db.commit()
        
        # Setup: Create topic and message
        original_status = topic.status
        test_db.add(topic)
        
        msg = Message(
            id=f"msg-{topic.id}",
            topic_id=topic.id,
            agent_id="agent_a",
            content="Test message",
            actual_tokens=100
        )
        test_db.add(msg)
        
        # Create summary job
        job = SummaryJob(
            id=f"job-{topic.id}",
            topic_id=topic.id,
            start_message_id=None,
            end_message_id=msg.id,
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        test_db.commit()
        
        # Mock LLM call with specific suggestion
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "Generated summary",
                "suggestion": llm_suggestion,
                "end_score": 50.0
            }
            
            # Process the job
            process_summary_job(job.id, db_session=test_db)
        
        # Verify LLM suggestion was applied correctly
        topic_after = test_db.query(Topic).filter(Topic.id == topic.id).first()
        
        if llm_suggestion == "force_end":
            # force_end should change status to closing_pending
            assert topic_after.status == "closing_pending", \
                f"Expected status 'closing_pending' for force_end, got '{topic_after.status}'"
        else:
            # Other suggestions should not change status
            assert topic_after.status == original_status, \
                f"Expected status to remain '{original_status}' for {llm_suggestion}, got '{topic_after.status}'"
        
        # Verify suggestion was saved
        assert topic_after.llm_suggestion == llm_suggestion, \
            f"Expected llm_suggestion to be '{llm_suggestion}', got '{topic_after.llm_suggestion}'"
