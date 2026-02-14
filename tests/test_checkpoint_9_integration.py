"""
Checkpoint 9 Integration Tests - Service Layer and Queue Integration Verification

This test suite verifies the complete integration of MessageService, SummaryService,
and QueueService, ensuring they work together correctly.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from services.message_service import MessageService
from services.summary_service import SummaryService
from services.queue_service import QueueService
from services.topic_service import TopicService
from models.models import Topic, Message, SummaryJob, Agent
from config.settings import settings


class TestServiceLayerIntegration:
    """Integration tests for service layer components."""
    
    def test_message_to_summary_job_flow(self, test_db: Session):
        """
        Test complete flow: message submission → token threshold → summary job creation.
        
        Validates:
        - MessageService correctly creates messages
        - Token count is updated correctly
        - SummaryJob is created when threshold is reached
        - pending_summary_job flag is set correctly
        """
        # Setup: Create topic and agent
        topic = Topic(
            id="test-topic-1",
            title="Test Topic",
            status="active",
            summary="",
            llm_suggestion="continue",
            end_score=0.0,
            token_count_since_summary=0,
            summary_threshold=100,  # Low threshold for testing
            last_summarized_message_id=None,
            pending_summary_job=False,
            agent_a_wants_close=False,
            agent_b_wants_close=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(topic)
        
        agent = Agent(
            id="agent-1",
            name="Test Agent",
            auth_token_hash="test_hash",
            created_at=datetime.utcnow()
        )
        test_db.add(agent)
        test_db.commit()
        
        # Initialize services
        message_service = MessageService(test_db)
        
        # Step 1: Submit messages below threshold
        message1 = message_service.create_message(
            topic_id=topic.id,
            agent_id=agent.id,
            content="First message",
            actual_tokens=40
        )
        
        # Verify: Token count updated, no summary job yet
        test_db.refresh(topic)
        assert topic.token_count_since_summary == 40
        assert topic.pending_summary_job is False
        
        job_count = test_db.query(SummaryJob).filter(
            SummaryJob.topic_id == topic.id
        ).count()
        assert job_count == 0
        
        # Step 2: Submit message that crosses threshold
        message2 = message_service.create_message(
            topic_id=topic.id,
            agent_id=agent.id,
            content="Second message that crosses threshold",
            actual_tokens=70
        )
        
        # Verify: Token count updated, summary job created
        test_db.refresh(topic)
        assert topic.token_count_since_summary == 110  # 40 + 70
        assert topic.pending_summary_job is True
        
        # Verify summary job was created
        summary_jobs = test_db.query(SummaryJob).filter(
            SummaryJob.topic_id == topic.id
        ).all()
        assert len(summary_jobs) == 1
        
        job = summary_jobs[0]
        assert job.status == "pending"
        assert job.start_message_id is None  # First summary
        assert job.end_message_id == message2.id
        assert job.retry_count == 0
        
        # Step 3: Verify no duplicate job is created
        message3 = message_service.create_message(
            topic_id=topic.id,
            agent_id=agent.id,
            content="Third message",
            actual_tokens=50
        )
        
        test_db.refresh(topic)
        assert topic.token_count_since_summary == 160  # 110 + 50
        assert topic.pending_summary_job is True  # Still true
        
        # Still only one job
        job_count = test_db.query(SummaryJob).filter(
            SummaryJob.topic_id == topic.id
        ).count()
        assert job_count == 1
    
    def test_summary_service_generates_correct_summary(self, test_db: Session):
        """
        Test SummaryService correctly generates summaries and updates topic.
        
        Validates:
        - SummaryService can generate summaries from messages
        - Topic summary is updated correctly
        - Summary history is preserved
        - LLM suggestions are applied correctly
        """
        # Setup: Create topic with messages
        topic = Topic(
            id="test-topic-2",
            title="Test Topic 2",
            status="active",
            summary="Old summary",
            llm_suggestion="continue",
            end_score=0.0,
            token_count_since_summary=100,
            summary_threshold=None,
            last_summarized_message_id=None,
            pending_summary_job=False,
            agent_a_wants_close=False,
            agent_b_wants_close=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(topic)
        
        messages = [
            Message(
                id=f"msg-{i}",
                topic_id=topic.id,
                agent_id="agent-1",
                content=f"Message {i}",
                actual_tokens=20,
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]
        for msg in messages:
            test_db.add(msg)
        
        test_db.commit()
        
        # Initialize service
        summary_service = SummaryService(test_db)
        
        # Mock LLM API call
        with patch.object(summary_service, '_call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "New comprehensive summary",
                "suggestion": "continue",
                "end_score": 25.0
            }
            
            # Generate summary
            result = summary_service.generate_summary(topic, messages)
            
            # Verify result
            assert result.summary == "New comprehensive summary"
            assert result.suggestion == "continue"
            assert result.end_score == 25.0
            
            # Verify LLM was called with correct prompt
            mock_llm.assert_called_once()
            call_args = mock_llm.call_args[0][0]
            assert "Old summary" in call_args
            assert "Message 0" in call_args
            assert "Message 1" in call_args
            assert "Message 2" in call_args
        
        # Update topic summary
        summary_service.update_topic_summary(
            topic_id=topic.id,
            summary=result.summary,
            suggestion=result.suggestion,
            end_score=result.end_score
        )
        
        # Verify topic was updated
        test_db.refresh(topic)
        assert topic.summary == "New comprehensive summary"
        assert topic.llm_suggestion == "continue"
        assert topic.end_score == 25.0
    
    def test_queue_service_manages_jobs_correctly(self, test_db: Session):
        """
        Test QueueService correctly manages summary jobs.
        
        Validates:
        - QueueService can enqueue jobs
        - Job status can be queried
        - Pending jobs can be retrieved
        - Job status can be updated
        """
        # Setup: Create topic
        topic = Topic(
            id="test-topic-3",
            title="Test Topic 3",
            status="active",
            summary="",
            llm_suggestion="continue",
            end_score=0.0,
            token_count_since_summary=0,
            summary_threshold=None,
            last_summarized_message_id=None,
            pending_summary_job=False,
            agent_a_wants_close=False,
            agent_b_wants_close=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(topic)
        test_db.commit()
        
        # Initialize service
        queue_service = QueueService(test_db)
        
        # Enqueue a job
        job_id = queue_service.enqueue_summary_job(
            topic_id=topic.id,
            start_message_id=None,
            end_message_id="msg-1"
        )
        
        # Verify job was created
        assert job_id is not None
        
        # Get job status
        job = queue_service.get_job_status(job_id)
        assert job is not None
        assert job["status"] == "pending"
        assert job["topic_id"] == topic.id
        
        # Get pending jobs
        pending_jobs = queue_service.get_pending_jobs(limit=10)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].id == job_id
        
        # Update job status
        success = queue_service.update_job_status(
            job_id=job_id,
            status="processing"
        )
        assert success is True
        
        # Verify status was updated
        job = queue_service.get_job_status(job_id)
        assert job["status"] == "processing"
        
        # Verify no longer in pending jobs
        pending_jobs = queue_service.get_pending_jobs(limit=10)
        assert len(pending_jobs) == 0
    
    def test_complete_integration_flow(self, test_db: Session):
        """
        Test complete integration: message → threshold → job → summary → update.
        
        This is the most comprehensive test that validates the entire flow
        from message submission to summary completion.
        """
        # Setup: Create topic and agent
        topic = Topic(
            id="test-topic-4",
            title="Integration Test Topic",
            status="active",
            summary="Initial summary",
            llm_suggestion="continue",
            end_score=0.0,
            token_count_since_summary=0,
            summary_threshold=50,  # Low threshold
            last_summarized_message_id=None,
            pending_summary_job=False,
            agent_a_wants_close=False,
            agent_b_wants_close=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(topic)
        
        agent = Agent(
            id="agent-1",
            name="Test Agent",
            auth_token_hash="test_hash",
            created_at=datetime.utcnow()
        )
        test_db.add(agent)
        test_db.commit()
        
        # Initialize services
        message_service = MessageService(test_db)
        summary_service = SummaryService(test_db)
        queue_service = QueueService(test_db)
        
        # Step 1: Submit message that triggers summary job
        message = message_service.create_message(
            topic_id=topic.id,
            agent_id=agent.id,
            content="Message that triggers summary",
            actual_tokens=60
        )
        
        # Verify job was created
        test_db.refresh(topic)
        assert topic.pending_summary_job is True
        
        pending_jobs = queue_service.get_pending_jobs(limit=10)
        assert len(pending_jobs) == 1
        job = pending_jobs[0]
        
        # Step 2: Simulate worker processing the job
        queue_service.update_job_status(job.id, "processing")
        
        # Get messages for summary
        messages = message_service.get_messages(topic.id, limit=100)
        assert len(messages) == 1
        
        # Generate summary (mock LLM)
        with patch.object(summary_service, '_call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "Updated summary after processing",
                "suggestion": "continue",
                "end_score": 30.0
            }
            
            result = summary_service.generate_summary(topic, messages)
        
        # Step 3: Update topic with summary
        summary_service.update_topic_summary(
            topic_id=topic.id,
            summary=result.summary,
            suggestion=result.suggestion,
            end_score=result.end_score
        )
        
        # Save history
        summary_service.save_summary_history(
            topic_id=topic.id,
            summary=result.summary,
            suggestion=result.suggestion,
            end_score=result.end_score
        )
        
        # Step 4: Complete the job and reset topic state
        queue_service.update_job_status(job.id, "done")
        
        # Reset topic state (simulating worker completion)
        test_db.refresh(topic)
        topic.pending_summary_job = False
        topic.token_count_since_summary = 0
        topic.last_summarized_message_id = message.id
        test_db.commit()
        
        # Step 5: Verify final state
        test_db.refresh(topic)
        assert topic.summary == "Updated summary after processing"
        assert topic.llm_suggestion == "continue"
        assert topic.end_score == 30.0
        assert topic.pending_summary_job is False
        assert topic.token_count_since_summary == 0
        assert topic.last_summarized_message_id == message.id
        
        # Verify job is done
        job_status = queue_service.get_job_status(job.id)
        assert job_status["status"] == "done"
        
        # Verify history was saved
        history = summary_service.get_summary_history(topic.id, limit=10)
        assert len(history) == 1
        assert history[0].summary == "Updated summary after processing"
        
        # Step 6: Verify new messages can be submitted
        message2 = message_service.create_message(
            topic_id=topic.id,
            agent_id=agent.id,
            content="New message after summary",
            actual_tokens=30
        )
        
        test_db.refresh(topic)
        assert topic.token_count_since_summary == 30
        assert topic.pending_summary_job is False  # Below threshold
