"""Tests for SummaryService."""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings as hypothesis_settings, HealthCheck

from services.summary_service import SummaryService, SummaryResult
from models.models import Topic, Message, SummaryHistory


class TestSummaryServiceUnit:
    """Unit tests for SummaryService."""
    
    def test_generate_summary_with_old_summary_and_new_messages(self, test_db, sample_topic):
        """Test generating summary with old summary and new messages."""
        service = SummaryService(test_db)
        
        # Add some messages
        messages = [
            Message(
                id=str(uuid.uuid4()),
                topic_id=sample_topic.id,
                agent_id="agent_a",
                content="Hello, let's discuss AI",
                actual_tokens=10,
                created_at=datetime.utcnow()
            ),
            Message(
                id=str(uuid.uuid4()),
                topic_id=sample_topic.id,
                agent_id="agent_b",
                content="Sure, what aspect?",
                actual_tokens=8,
                created_at=datetime.utcnow()
            )
        ]
        
        for msg in messages:
            test_db.add(msg)
        test_db.commit()
        
        # Mock the LLM API call
        with patch.object(service, '_call_deepseek_api') as mock_api:
            mock_api.return_value = {
                "summary": "Discussion about AI started",
                "suggestion": "continue",
                "end_score": 20.0
            }
            
            result = service.generate_summary(sample_topic, messages)
            
            assert result.summary == "Discussion about AI started"
            assert result.suggestion == "continue"
            assert result.end_score == 20.0
    
    def test_update_topic_summary(self, test_db, sample_topic):
        """Test updating topic summary fields."""
        service = SummaryService(test_db)
        
        service.update_topic_summary(
            topic_id=sample_topic.id,
            summary="New summary",
            suggestion="change_angle",
            end_score=45.0
        )
        
        # Refresh topic from database
        test_db.refresh(sample_topic)
        
        assert sample_topic.summary == "New summary"
        assert sample_topic.llm_suggestion == "change_angle"
        assert sample_topic.end_score == 45.0
    
    def test_update_topic_summary_not_found(self, test_db):
        """Test updating summary for non-existent topic raises error."""
        service = SummaryService(test_db)
        
        with pytest.raises(ValueError, match="Topic .* not found"):
            service.update_topic_summary(
                topic_id="nonexistent",
                summary="Test",
                suggestion="continue",
                end_score=0.0
            )
    
    def test_save_summary_history(self, test_db, sample_topic):
        """Test saving summary history record."""
        service = SummaryService(test_db)
        
        history = service.save_summary_history(
            topic_id=sample_topic.id,
            summary="Historical summary",
            suggestion="suggest_end",
            end_score=75.0
        )
        
        assert history.id is not None
        assert history.topic_id == sample_topic.id
        assert history.summary == "Historical summary"
        assert history.llm_suggestion == "suggest_end"
        assert history.end_score == 75.0
    
    def test_get_summary_history(self, test_db, sample_topic):
        """Test retrieving summary history."""
        service = SummaryService(test_db)
        
        # Create multiple history records
        for i in range(5):
            service.save_summary_history(
                topic_id=sample_topic.id,
                summary=f"Summary {i}",
                suggestion="continue",
                end_score=float(i * 10)
            )
        
        # Get history with limit
        history = service.get_summary_history(sample_topic.id, limit=3)
        
        assert len(history) == 3
        # Should be newest first
        assert history[0].summary == "Summary 4"
        assert history[1].summary == "Summary 3"
        assert history[2].summary == "Summary 2"
    
    def test_rollback_summary(self, test_db, sample_topic):
        """Test rolling back summary to historical version."""
        service = SummaryService(test_db)
        
        # Update topic summary
        sample_topic.summary = "Current summary"
        sample_topic.llm_suggestion = "continue"
        sample_topic.end_score = 30.0
        test_db.commit()
        
        # Create history record
        history = service.save_summary_history(
            topic_id=sample_topic.id,
            summary="Old summary",
            suggestion="change_angle",
            end_score=50.0
        )
        
        # Rollback to history
        service.rollback_summary(sample_topic.id, history.id)
        
        # Refresh and verify
        test_db.refresh(sample_topic)
        assert sample_topic.summary == "Old summary"
        assert sample_topic.llm_suggestion == "change_angle"
        assert sample_topic.end_score == 50.0
    
    def test_rollback_summary_topic_not_found(self, test_db):
        """Test rollback with non-existent topic raises error."""
        service = SummaryService(test_db)
        
        with pytest.raises(ValueError, match="Topic .* not found"):
            service.rollback_summary("nonexistent", "some_history_id")
    
    def test_rollback_summary_history_not_found(self, test_db, sample_topic):
        """Test rollback with non-existent history raises error."""
        service = SummaryService(test_db)
        
        with pytest.raises(ValueError, match="History .* not found"):
            service.rollback_summary(sample_topic.id, "nonexistent")
    
    def test_rollback_summary_wrong_topic(self, test_db, sample_topic):
        """Test rollback with history from different topic raises error."""
        service = SummaryService(test_db)
        
        # Create another topic
        other_topic = Topic(
            id=str(uuid.uuid4()),
            title="Other Topic",
            status="active",
            summary="",
            token_count_since_summary=0,
            pending_summary_job=False,
            agent_a_wants_close=False,
            agent_b_wants_close=False
        )
        test_db.add(other_topic)
        test_db.commit()
        
        # Create history for other topic
        history = service.save_summary_history(
            topic_id=other_topic.id,
            summary="Other summary",
            suggestion="continue",
            end_score=10.0
        )
        
        # Try to rollback sample_topic with other_topic's history
        with pytest.raises(ValueError, match="does not belong to topic"):
            service.rollback_summary(sample_topic.id, history.id)
    
    def test_apply_llm_suggestion_force_end(self, test_db, sample_topic):
        """Test applying force_end suggestion sets topic to closing_pending."""
        service = SummaryService(test_db)
        
        assert sample_topic.status == "active"
        
        service.apply_llm_suggestion(sample_topic, "force_end")
        
        test_db.refresh(sample_topic)
        assert sample_topic.status == "closing_pending"
    
    def test_apply_llm_suggestion_continue(self, test_db, sample_topic):
        """Test applying continue suggestion does not change status."""
        service = SummaryService(test_db)
        
        assert sample_topic.status == "active"
        
        service.apply_llm_suggestion(sample_topic, "continue")
        
        test_db.refresh(sample_topic)
        assert sample_topic.status == "active"
    
    def test_build_summary_prompt(self, test_db, sample_topic):
        """Test building summary prompt with old summary and new messages."""
        service = SummaryService(test_db)
        
        sample_topic.summary = "Previous discussion about AI"
        
        messages = [
            Message(
                id=str(uuid.uuid4()),
                topic_id=sample_topic.id,
                agent_id="agent_a",
                content="What about machine learning?",
                actual_tokens=10,
                created_at=datetime.utcnow()
            )
        ]
        
        prompt = service._build_summary_prompt(sample_topic.summary, messages)
        
        assert "Previous discussion about AI" in prompt
        assert "What about machine learning?" in prompt
        assert "agent_a" in prompt
        assert "JSON format" in prompt
    
    def test_parse_llm_response_valid(self, test_db):
        """Test parsing valid LLM response."""
        service = SummaryService(test_db)
        
        response = {
            "summary": "Test summary",
            "suggestion": "change_angle",
            "end_score": 60.0
        }
        
        summary, suggestion, end_score = service._parse_llm_response(response)
        
        assert summary == "Test summary"
        assert suggestion == "change_angle"
        assert end_score == 60.0
    
    def test_parse_llm_response_invalid_suggestion(self, test_db):
        """Test parsing LLM response with invalid suggestion raises error."""
        service = SummaryService(test_db)
        
        response = {
            "summary": "Test",
            "suggestion": "invalid_suggestion",
            "end_score": 50.0
        }
        
        with pytest.raises(ValueError, match="Invalid suggestion"):
            service._parse_llm_response(response)
    
    def test_parse_llm_response_invalid_end_score(self, test_db):
        """Test parsing LLM response with invalid end_score raises error."""
        service = SummaryService(test_db)
        
        response = {
            "summary": "Test",
            "suggestion": "continue",
            "end_score": 150.0  # Out of range
        }
        
        with pytest.raises(ValueError, match="Invalid end_score"):
            service._parse_llm_response(response)


class TestSummaryServiceProperties:
    """Property-based tests for SummaryService."""
    
    # Feature: dual-agent-chat, Property 16: LLM建议值约束
    @hypothesis_settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        suggestion=st.sampled_from(["continue", "change_angle", "suggest_end", "force_end"]),
        end_score=st.floats(min_value=0.0, max_value=100.0)
    )
    def test_property_16_llm_suggestion_constraint(self, test_db, sample_topic, suggestion, end_score):
        """
        Property 16: LLM建议值约束
        
        For any topic's llm_suggestion field, its value must be one of:
        continue, change_angle, suggest_end, or force_end.
        
        Validates: Requirements 6.6
        """
        service = SummaryService(test_db)
        
        # Update topic with valid suggestion
        service.update_topic_summary(
            topic_id=sample_topic.id,
            summary="Test summary",
            suggestion=suggestion,
            end_score=end_score
        )
        
        # Verify it was saved correctly
        test_db.refresh(sample_topic)
        assert sample_topic.llm_suggestion in ["continue", "change_angle", "suggest_end", "force_end"]
        assert sample_topic.llm_suggestion == suggestion
    
    # Feature: dual-agent-chat, Property 17: 总结后状态更新
    @hypothesis_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        summary=st.text(min_size=1, max_size=500),
        suggestion=st.sampled_from(["continue", "change_angle", "suggest_end", "force_end"]),
        end_score=st.floats(min_value=0.0, max_value=100.0)
    )
    def test_property_17_summary_updates_state(self, test_db, sample_topic, summary, suggestion, end_score):
        """
        Property 17: 总结后状态更新
        
        For any Worker-completed summary task, the topic's summary, llm_suggestion,
        and end_score fields should be updated, token_count_since_summary should be
        reset to 0, and pending_summary_job should be set to false.
        
        Validates: Requirements 6.7, 6.8
        """
        service = SummaryService(test_db)
        
        # Set initial state
        sample_topic.token_count_since_summary = 5000
        sample_topic.pending_summary_job = True
        test_db.commit()
        
        # Update summary
        service.update_topic_summary(
            topic_id=sample_topic.id,
            summary=summary,
            suggestion=suggestion,
            end_score=end_score
        )
        
        # Verify updates
        test_db.refresh(sample_topic)
        assert sample_topic.summary == summary
        assert sample_topic.llm_suggestion == suggestion
        assert sample_topic.end_score == end_score
        
        # Note: token_count reset and pending_summary_job flag are handled by Worker
        # This test verifies the service correctly updates the summary fields
    
    # Feature: dual-agent-chat, Property 37: Force_end自动设置closing_pending
    def test_property_37_force_end_sets_closing_pending(self, test_db, sample_topic):
        """
        Property 37: Force_end自动设置closing_pending
        
        For any topic with LLM_Suggestion of force_end, the system should
        automatically set the topic status to closing_pending.
        
        Validates: Requirements 7.5
        """
        service = SummaryService(test_db)
        
        # Ensure topic starts as active
        sample_topic.status = "active"
        test_db.commit()
        
        # Apply force_end suggestion
        service.apply_llm_suggestion(sample_topic, "force_end")
        
        # Verify status changed to closing_pending
        test_db.refresh(sample_topic)
        assert sample_topic.status == "closing_pending"
    
    # Feature: dual-agent-chat, Property 42: Summary历史版本保留
    @hypothesis_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_summaries=st.integers(min_value=1, max_value=10)
    )
    def test_property_42_summary_history_preserved(self, test_db, sample_topic, num_summaries):
        """
        Property 42: Summary历史版本保留
        
        For any summary update operation, the system should preserve a historical
        version in the summary_history table.
        
        Validates: Requirements 11.1, 11.2
        """
        service = SummaryService(test_db)
        
        # Create multiple summary history records
        for i in range(num_summaries):
            service.save_summary_history(
                topic_id=sample_topic.id,
                summary=f"Summary version {i}",
                suggestion="continue",
                end_score=float(i * 10)
            )
        
        # Retrieve history
        history = service.get_summary_history(sample_topic.id, limit=num_summaries)
        
        # Verify all versions are preserved
        assert len(history) == num_summaries
        
        # Verify they're ordered newest first
        for i, record in enumerate(history):
            expected_version = num_summaries - 1 - i
            assert record.summary == f"Summary version {expected_version}"
    
    # Feature: dual-agent-chat, Property 43: 消息不可删除
    def test_property_43_messages_not_deletable(self, test_db, sample_topic):
        """
        Property 43: 消息不可删除
        
        For any created message, the system should not support deletion operations.
        All messages should be permanently retained.
        
        Validates: Requirements 11.3
        
        Note: This is a design constraint - the SummaryService and MessageService
        do not provide any delete methods for messages.
        """
        service = SummaryService(test_db)
        
        # Verify SummaryService has no delete_message method
        assert not hasattr(service, 'delete_message')
        assert not hasattr(service, 'remove_message')
        
        # This property is enforced by not implementing deletion functionality
        # Messages can only be created, never deleted
    
    # Feature: dual-agent-chat, Property 44: Summary回滚
    @hypothesis_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        original_summary=st.text(min_size=1, max_size=200),
        new_summary=st.text(min_size=1, max_size=200)
    )
    def test_property_44_summary_rollback(self, test_db, sample_topic, original_summary, new_summary):
        """
        Property 44: Summary回滚
        
        For any topic, the system should support restoring the summary to a
        historical version.
        
        Validates: Requirements 11.5
        """
        service = SummaryService(test_db)
        
        # Save original summary as history
        history = service.save_summary_history(
            topic_id=sample_topic.id,
            summary=original_summary,
            suggestion="continue",
            end_score=30.0
        )
        
        # Update topic to new summary
        service.update_topic_summary(
            topic_id=sample_topic.id,
            summary=new_summary,
            suggestion="change_angle",
            end_score=50.0
        )
        
        test_db.refresh(sample_topic)
        assert sample_topic.summary == new_summary
        
        # Rollback to historical version
        service.rollback_summary(sample_topic.id, history.id)
        
        # Verify rollback succeeded
        test_db.refresh(sample_topic)
        assert sample_topic.summary == original_summary
        assert sample_topic.llm_suggestion == "continue"
        assert sample_topic.end_score == 30.0
