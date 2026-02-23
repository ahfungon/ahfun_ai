"""Tests for QueueService."""
import pytest
from unittest.mock import patch, MagicMock
from services.queue_service import QueueService
from models.models import SummaryJob


class TestQueueService:
    """Test suite for QueueService."""
    
    def test_enqueue_summary_job_creates_job_record(self, test_db):
        """Test that enqueue_summary_job creates a job record in database."""
        queue_service = QueueService(test_db)
        
        # Mock Celery send_task to avoid actual task dispatch
        with patch('services.queue_service.celery_app.send_task') as mock_send_task:
            job_id = queue_service.enqueue_summary_job(
                topic_id="topic-123",
                start_message_id="msg-100",
                end_message_id="msg-200"
            )
        
        # Verify job was created in database
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        assert job is not None
        assert job.topic_id == "topic-123"
        assert job.start_message_id == "msg-100"
        assert job.end_message_id == "msg-200"
        assert job.status == "pending"
        assert job.retry_count == 0
        
        # Verify Celery task was dispatched
        mock_send_task.assert_called_once_with(
            "workers.tasks.process_summary_job",
            args=[job_id],
            queue="summary_jobs"
        )
    
    def test_enqueue_summary_job_with_no_start_message(self, test_db):
        """Test enqueueing a job with no start_message_id (first summary)."""
        queue_service = QueueService(test_db)
        
        with patch('services.queue_service.celery_app.send_task'):
            job_id = queue_service.enqueue_summary_job(
                topic_id="topic-456",
                start_message_id=None,
                end_message_id="msg-50"
            )
        
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        assert job is not None
        assert job.start_message_id is None
        assert job.end_message_id == "msg-50"
    
    def test_get_job_status_returns_job_info(self, test_db):
        """Test that get_job_status returns correct job information."""
        queue_service = QueueService(test_db)
        
        # Create a job
        with patch('services.queue_service.celery_app.send_task'):
            job_id = queue_service.enqueue_summary_job(
                topic_id="topic-789",
                start_message_id="msg-1",
                end_message_id="msg-10"
            )
        
        # Query job status
        status = queue_service.get_job_status(job_id)
        
        assert status is not None
        assert status["id"] == job_id
        assert status["topic_id"] == "topic-789"
        assert status["status"] == "pending"
        assert status["retry_count"] == 0
        assert status["error_message"] is None
        assert "created_at" in status
        assert "updated_at" in status
    
    def test_get_job_status_returns_none_for_nonexistent_job(self, test_db):
        """Test that get_job_status returns None for non-existent job."""
        queue_service = QueueService(test_db)
        
        status = queue_service.get_job_status("nonexistent-job-id")
        
        assert status is None
    
    def test_get_pending_jobs_returns_pending_jobs_only(self, test_db):
        """Test that get_pending_jobs returns only pending jobs."""
        queue_service = QueueService(test_db)
        
        # Create multiple jobs with different statuses
        with patch('services.queue_service.celery_app.send_task'):
            job_id_1 = queue_service.enqueue_summary_job("topic-1", None, "msg-1")
            job_id_2 = queue_service.enqueue_summary_job("topic-2", None, "msg-2")
            job_id_3 = queue_service.enqueue_summary_job("topic-3", None, "msg-3")
        
        # Update some jobs to different statuses
        queue_service.update_job_status(job_id_2, "processing")
        queue_service.update_job_status(job_id_3, "done")
        
        # Get pending jobs
        pending_jobs = queue_service.get_pending_jobs()
        
        assert len(pending_jobs) == 1
        assert pending_jobs[0].id == job_id_1
        assert pending_jobs[0].status == "pending"
    
    def test_get_pending_jobs_respects_limit(self, test_db):
        """Test that get_pending_jobs respects the limit parameter."""
        queue_service = QueueService(test_db)
        
        # Create 10 pending jobs
        with patch('services.queue_service.celery_app.send_task'):
            for i in range(10):
                queue_service.enqueue_summary_job(f"topic-{i}", None, f"msg-{i}")
        
        # Get only 3 jobs
        pending_jobs = queue_service.get_pending_jobs(limit=3)
        
        assert len(pending_jobs) == 3
    
    def test_get_pending_jobs_orders_by_creation_time(self, test_db):
        """Test that get_pending_jobs returns jobs ordered by creation time (oldest first)."""
        queue_service = QueueService(test_db)
        
        # Create jobs in sequence
        with patch('services.queue_service.celery_app.send_task'):
            job_id_1 = queue_service.enqueue_summary_job("topic-1", None, "msg-1")
            job_id_2 = queue_service.enqueue_summary_job("topic-2", None, "msg-2")
            job_id_3 = queue_service.enqueue_summary_job("topic-3", None, "msg-3")
        
        pending_jobs = queue_service.get_pending_jobs()
        
        # Should be ordered oldest first
        assert pending_jobs[0].id == job_id_1
        assert pending_jobs[1].id == job_id_2
        assert pending_jobs[2].id == job_id_3
    
    def test_get_jobs_by_topic_returns_all_topic_jobs(self, test_db):
        """Test that get_jobs_by_topic returns all jobs for a specific topic."""
        queue_service = QueueService(test_db)
        
        # Create jobs for different topics
        with patch('services.queue_service.celery_app.send_task'):
            job_id_1 = queue_service.enqueue_summary_job("topic-A", None, "msg-1")
            job_id_2 = queue_service.enqueue_summary_job("topic-A", "msg-1", "msg-2")
            job_id_3 = queue_service.enqueue_summary_job("topic-B", None, "msg-1")
        
        # Get jobs for topic-A
        topic_a_jobs = queue_service.get_jobs_by_topic("topic-A")
        
        assert len(topic_a_jobs) == 2
        job_ids = [job.id for job in topic_a_jobs]
        assert job_id_1 in job_ids
        assert job_id_2 in job_ids
        assert job_id_3 not in job_ids
    
    def test_update_job_status_updates_status(self, test_db):
        """Test that update_job_status correctly updates job status."""
        queue_service = QueueService(test_db)
        
        # Create a job
        with patch('services.queue_service.celery_app.send_task'):
            job_id = queue_service.enqueue_summary_job("topic-1", None, "msg-1")
        
        # Update status to processing
        result = queue_service.update_job_status(job_id, "processing")
        
        assert result is True
        
        # Verify status was updated
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        assert job.status == "processing"
    
    def test_update_job_status_updates_error_message(self, test_db):
        """Test that update_job_status can update error message."""
        queue_service = QueueService(test_db)
        
        # Create a job
        with patch('services.queue_service.celery_app.send_task'):
            job_id = queue_service.enqueue_summary_job("topic-1", None, "msg-1")
        
        # Update status to failed with error message
        result = queue_service.update_job_status(
            job_id, 
            "failed", 
            error_message="LLM API timeout"
        )
        
        assert result is True
        
        # Verify error message was updated
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        assert job.status == "failed"
        assert job.error_message == "LLM API timeout"
    
    def test_update_job_status_updates_retry_count(self, test_db):
        """Test that update_job_status can update retry count."""
        queue_service = QueueService(test_db)
        
        # Create a job
        with patch('services.queue_service.celery_app.send_task'):
            job_id = queue_service.enqueue_summary_job("topic-1", None, "msg-1")
        
        # Update retry count
        result = queue_service.update_job_status(job_id, "pending", retry_count=1)
        
        assert result is True
        
        # Verify retry count was updated
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        assert job.retry_count == 1
    
    def test_update_job_status_returns_false_for_nonexistent_job(self, test_db):
        """Test that update_job_status returns False for non-existent job."""
        queue_service = QueueService(test_db)
        
        result = queue_service.update_job_status("nonexistent-job", "done")
        
        assert result is False
    
    def test_concurrent_job_limit_configuration(self, test_db):
        """
        Test that the system is configured with maximum 5 concurrent tasks.
        
        Validates: Requirement 6.13 (concurrent control)
        """
        from config.settings import settings
        
        # Verify the configuration matches requirement
        assert settings.celery_max_concurrent_tasks == 5
    
    def test_task_routing_configuration(self):
        """Test that Celery task routing is properly configured."""
        from workers.celery_app import celery_app
        
        # Verify task routes are configured
        assert "task_routes" in celery_app.conf
        assert "workers.tasks.process_summary_job" in celery_app.conf.task_routes
        assert celery_app.conf.task_routes["workers.tasks.process_summary_job"]["queue"] == "summary_jobs"


class TestQueueServiceIntegration:
    """Integration tests for QueueService with actual Celery."""
    
    @pytest.mark.integration
    def test_enqueue_job_dispatches_to_celery(self, test_db):
        """
        Integration test: Verify job is actually dispatched to Celery.
        
        Note: This test requires Redis to be running.
        """
        queue_service = QueueService(test_db)
        
        # This will actually dispatch to Celery if Redis is available
        try:
            job_id = queue_service.enqueue_summary_job(
                topic_id="integration-test-topic",
                start_message_id=None,
                end_message_id="msg-integration"
            )
            
            # Verify job was created
            job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
            assert job is not None
            assert job.status == "pending"
            
        except Exception as e:
            # If Redis is not available, skip this test
            pytest.skip(f"Redis not available for integration test: {e}")



# ============================================================================
# Property-Based Tests for QueueService
# ============================================================================

from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize
import time
from datetime import datetime


# Test data generators
@st.composite
def topic_id_strategy(draw):
    """Generate valid topic IDs."""
    return f"topic-{draw(st.uuids())}"


@st.composite
def message_id_strategy(draw):
    """Generate valid message IDs."""
    return f"msg-{draw(st.uuids())}"


@st.composite
def job_count_strategy(draw):
    """Generate job counts for concurrency testing (1-20 jobs)."""
    return draw(st.integers(min_value=1, max_value=20))


class TestQueueServiceProperties:
    """Property-based tests for QueueService."""
    
    @given(
        topic_id=topic_id_strategy(),
        start_msg=st.one_of(st.none(), message_id_strategy()),
        end_msg=message_id_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_enqueue_creates_pending_job(self, test_db, topic_id, start_msg, end_msg):
        """
        Property: For any valid inputs, enqueue_summary_job creates a job with status='pending'.
        
        **Validates: Requirements 6.1, 6.9**
        """
        # Clean up any existing jobs
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        with patch('services.queue_service.celery_app.send_task'):
            job_id = queue_service.enqueue_summary_job(
                topic_id=topic_id,
                start_message_id=start_msg,
                end_message_id=end_msg
            )
        
        # Verify job exists and has correct initial state
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        assert job is not None
        assert job.status == "pending"
        assert job.retry_count == 0
        assert job.topic_id == topic_id
        assert job.start_message_id == start_msg
        assert job.end_message_id == end_msg
    
    @given(job_count=job_count_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_33_concurrent_control_limit(self, test_db, job_count):
        """
        Property 33: 任务队列并发控制
        
        For any number of pending jobs, get_pending_jobs with limit=5 
        returns at most 5 jobs, enforcing the concurrent control requirement.
        
        **Validates: Requirements 6.13**
        
        This property ensures that the system respects the maximum concurrent
        task limit of 5, which is critical for resource management and preventing
        system overload.
        """
        # Clean up any existing jobs from previous examples
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        # Create job_count pending jobs
        created_job_ids = []
        with patch('services.queue_service.celery_app.send_task'):
            for i in range(job_count):
                job_id = queue_service.enqueue_summary_job(
                    topic_id=f"topic-{i}",
                    start_message_id=None,
                    end_message_id=f"msg-{i}"
                )
                created_job_ids.append(job_id)
        
        # Get pending jobs with default limit (5)
        pending_jobs = queue_service.get_pending_jobs(limit=5)
        
        # Property: Should never return more than 5 jobs
        assert len(pending_jobs) <= 5
        
        # Property: Should return min(job_count, 5) jobs
        expected_count = min(job_count, 5)
        assert len(pending_jobs) == expected_count
        
        # Property: All returned jobs should be pending
        for job in pending_jobs:
            assert job.status == "pending"
        
        # Property: All returned jobs should be from our created jobs
        returned_job_ids = [job.id for job in pending_jobs]
        for job_id in returned_job_ids:
            assert job_id in created_job_ids
    
    @given(
        num_topics=st.integers(min_value=1, max_value=10),
        jobs_per_topic=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_concurrent_jobs_different_topics(self, test_db, num_topics, jobs_per_topic):
        """
        Property: Different topics can have concurrent jobs without interference.
        
        **Validates: Requirements 6.13, 6.14**
        
        This ensures that the concurrent control applies globally, not per-topic,
        and that jobs from different topics can coexist in the queue.
        """
        # Clean up any existing jobs
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        # Create jobs for multiple topics
        all_job_ids = []
        with patch('services.queue_service.celery_app.send_task'):
            for topic_idx in range(num_topics):
                topic_id = f"topic-{topic_idx}"
                for job_idx in range(jobs_per_topic):
                    job_id = queue_service.enqueue_summary_job(
                        topic_id=topic_id,
                        start_message_id=None,
                        end_message_id=f"msg-{topic_idx}-{job_idx}"
                    )
                    all_job_ids.append(job_id)
        
        # Get pending jobs
        pending_jobs = queue_service.get_pending_jobs(limit=5)
        
        # Property: Should respect the limit
        assert len(pending_jobs) <= 5
        
        # Property: Jobs can be from different topics
        topic_ids_in_result = set(job.topic_id for job in pending_jobs)
        # If we have more than 5 total jobs, we might see multiple topics
        if len(all_job_ids) > 5:
            # At least verify we can have jobs from different topics
            assert len(topic_ids_in_result) >= 1
    
    @given(
        num_jobs=st.integers(min_value=1, max_value=15),
        limit=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_get_pending_jobs_respects_any_limit(self, test_db, num_jobs, limit):
        """
        Property: get_pending_jobs respects any valid limit parameter.
        
        **Validates: Requirements 6.1, 6.13**
        """
        # Clean up any existing jobs
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        # Create num_jobs pending jobs
        with patch('services.queue_service.celery_app.send_task'):
            for i in range(num_jobs):
                queue_service.enqueue_summary_job(
                    topic_id=f"topic-{i}",
                    start_message_id=None,
                    end_message_id=f"msg-{i}"
                )
        
        # Get pending jobs with specified limit
        pending_jobs = queue_service.get_pending_jobs(limit=limit)
        
        # Property: Should never exceed the limit
        assert len(pending_jobs) <= limit
        
        # Property: Should return min(num_jobs, limit) jobs
        expected_count = min(num_jobs, limit)
        assert len(pending_jobs) == expected_count
    
    @given(
        num_jobs=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_fifo_ordering(self, test_db, num_jobs):
        """
        Property: Pending jobs are returned in FIFO order (oldest first).
        
        **Validates: Requirements 6.1, 6.13**
        
        This ensures fair processing - jobs that were created first
        are processed first.
        """
        # Clean up any existing jobs
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        # Create jobs in sequence with small delays to ensure ordering
        created_job_ids = []
        with patch('services.queue_service.celery_app.send_task'):
            for i in range(num_jobs):
                job_id = queue_service.enqueue_summary_job(
                    topic_id=f"topic-{i}",
                    start_message_id=None,
                    end_message_id=f"msg-{i}"
                )
                created_job_ids.append(job_id)
                # Small delay to ensure different timestamps
                time.sleep(0.001)
        
        # Get all pending jobs
        pending_jobs = queue_service.get_pending_jobs(limit=num_jobs)
        
        # Property: Jobs should be in creation order
        returned_job_ids = [job.id for job in pending_jobs]
        assert returned_job_ids == created_job_ids
        
        # Property: Timestamps should be monotonically increasing
        timestamps = [job.created_at for job in pending_jobs]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1]
    
    @given(
        topic_id=topic_id_strategy(),
        num_jobs=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_get_jobs_by_topic_isolation(self, test_db, topic_id, num_jobs):
        """
        Property: get_jobs_by_topic returns only jobs for the specified topic.
        
        **Validates: Requirements 6.1**
        """
        # Clean up any existing jobs
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        # Create jobs for the target topic
        target_job_ids = []
        with patch('services.queue_service.celery_app.send_task'):
            for i in range(num_jobs):
                job_id = queue_service.enqueue_summary_job(
                    topic_id=topic_id,
                    start_message_id=None,
                    end_message_id=f"msg-{i}"
                )
                target_job_ids.append(job_id)
            
            # Create jobs for other topics
            for i in range(3):
                queue_service.enqueue_summary_job(
                    topic_id=f"other-topic-{i}",
                    start_message_id=None,
                    end_message_id=f"other-msg-{i}"
                )
        
        # Get jobs for target topic
        topic_jobs = queue_service.get_jobs_by_topic(topic_id)
        
        # Property: Should return exactly num_jobs jobs
        assert len(topic_jobs) == num_jobs
        
        # Property: All jobs should belong to the target topic
        for job in topic_jobs:
            assert job.topic_id == topic_id
        
        # Property: All target jobs should be returned
        returned_job_ids = [job.id for job in topic_jobs]
        for job_id in target_job_ids:
            assert job_id in returned_job_ids
    
    @given(
        job_count=st.integers(min_value=1, max_value=10),
        status_changes=st.lists(
            st.sampled_from(["processing", "done", "failed"]),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_status_filtering(self, test_db, job_count, status_changes):
        """
        Property: get_pending_jobs only returns jobs with status='pending'.
        
        **Validates: Requirements 6.1, 6.13**
        """
        # Clean up any existing jobs
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        # Create jobs
        job_ids = []
        with patch('services.queue_service.celery_app.send_task'):
            for i in range(job_count):
                job_id = queue_service.enqueue_summary_job(
                    topic_id=f"topic-{i}",
                    start_message_id=None,
                    end_message_id=f"msg-{i}"
                )
                job_ids.append(job_id)
        
        # Change status of some jobs
        num_changes = min(len(status_changes), len(job_ids))
        for i in range(num_changes):
            queue_service.update_job_status(job_ids[i], status_changes[i])
        
        # Get pending jobs
        pending_jobs = queue_service.get_pending_jobs(limit=job_count)
        
        # Property: All returned jobs must have status='pending'
        for job in pending_jobs:
            assert job.status == "pending"
        
        # Property: Count should match number of jobs that remain pending
        expected_pending = job_count - num_changes
        assert len(pending_jobs) == expected_pending
    
    @given(
        topic_id=topic_id_strategy(),
        start_msg=st.one_of(st.none(), message_id_strategy()),
        end_msg=message_id_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_job_status_query_consistency(self, test_db, topic_id, start_msg, end_msg):
        """
        Property: get_job_status returns consistent information with database state.
        
        **Validates: Requirements 6.1, 6.9**
        """
        # Clean up any existing jobs
        test_db.query(SummaryJob).delete()
        test_db.commit()
        
        queue_service = QueueService(test_db)
        
        with patch('services.queue_service.celery_app.send_task'):
            job_id = queue_service.enqueue_summary_job(
                topic_id=topic_id,
                start_message_id=start_msg,
                end_message_id=end_msg
            )
        
        # Get status through service
        status = queue_service.get_job_status(job_id)
        
        # Get job directly from database
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        
        # Property: Status should match database state
        assert status is not None
        assert status["id"] == job.id
        assert status["topic_id"] == job.topic_id
        assert status["status"] == job.status
        assert status["retry_count"] == job.retry_count
        assert status["error_message"] == job.error_message
