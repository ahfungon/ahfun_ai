"""Property-based tests for TopicService.

This test suite validates the TopicService implementation using hypothesis
for property-based testing, covering properties 3, 4, 6, 19, 39, 40, and 41
from the design document.
"""
import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, HealthCheck
from hypothesis import settings as hypothesis_settings
from uuid import uuid4

from services.topic_service import TopicService, CloseStatus, ClosingStatusDetail
from models.models import Topic, Message
from config.settings import settings


# Test data generators
@st.composite
def topic_title_strategy(draw):
    """Generate valid topic titles."""
    return draw(st.one_of(
        st.none(),
        st.text(min_size=1, max_size=255)
    ))


@st.composite
def agent_id_strategy(draw):
    """Generate valid agent IDs."""
    return draw(st.text(min_size=1, max_size=36, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-'
    )))


# Property 3: New topic initial state
class TestProperty3NewTopicInitialState:
    """**Validates: Requirements 1.3, 9.1**
    
    Property 3: For any newly created topic, its cumulative summary should be 
    an empty string, token_count_since_summary should be 0, status should be 
    'active', and pending_summary_job should be false.
    """
    
    @given(title=topic_title_strategy())
    @hypothesis_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_new_topic_has_correct_initial_state(self, test_db, title):
        """Test that newly created topics have correct initial state."""
        service = TopicService(test_db)
        
        # Create topic with or without title
        topic = service.create_topic(title=title)
        
        # Verify initial state
        assert topic.summary == "", "New topic should have empty summary"
        assert topic.token_count_since_summary == 0, "New topic should have 0 token count"
        assert topic.status == "active", "New topic should be active"
        assert topic.pending_summary_job is False, "New topic should not have pending job"
        assert topic.agent_a_wants_close is False, "New topic should not have agent_a wanting close"
        assert topic.agent_b_wants_close is False, "New topic should not have agent_b wanting close"
        assert topic.closing_requested_by is None, "New topic should not have closing requester"
        assert topic.closing_requested_at is None, "New topic should not have closing request time"
        
        # Verify title handling
        if title is None:
            assert topic.title.startswith("Discussion Topic"), "Default title should be generated"
        else:
            assert topic.title == title, "Provided title should be used"
    
    def test_new_topic_without_title_generates_default(self, test_db):
        """Test that creating topic without title generates default title."""
        service = TopicService(test_db)
        topic = service.create_topic()
        
        assert topic.title is not None
        assert len(topic.title) > 0
        assert "Discussion Topic" in topic.title


# Property 4: Closed topic rejects messages
class TestProperty4ClosedTopicRejectsMessages:
    """**Validates: Requirements 1.5, 5.5**
    
    Property 4: For any topic with status 'closed', attempting to submit a new 
    message should be rejected and return an error.
    
    Note: This property is tested at the service level by verifying that closed
    topics cannot be retrieved as active topics, which is the mechanism that
    prevents message submission.
    """
    
    def test_closed_topic_not_returned_as_active(self, test_db):
        """Test that closed topics are not returned by get_active_topic."""
        service = TopicService(test_db)
        
        # Create and close a topic
        topic = service.create_topic(title="Test Topic")
        service.close_topic(topic.id)
        
        # Verify closed topic is not returned as active
        active_topic = service.get_active_topic()
        assert active_topic is None or active_topic.id != topic.id
    
    def test_multiple_closed_topics_not_returned(self, test_db):
        """Test that multiple closed topics are not returned as active."""
        service = TopicService(test_db)
        
        # Create and close multiple topics
        topic1 = service.create_topic(title="Topic 1")
        topic2 = service.create_topic(title="Topic 2")
        service.close_topic(topic1.id)
        service.close_topic(topic2.id)
        
        # Verify no closed topics are returned
        active_topic = service.get_active_topic()
        assert active_topic is None


# Property 6: Active topic query correctness
class TestProperty6ActiveTopicQueryCorrectness:
    """**Validates: Requirements 3.1, 3.2, 3.4**
    
    Property 6: For any topic query request, the returned topic (if exists) 
    must have status 'active' or 'closing_pending', and the response must 
    include topic ID, title, cumulative summary, LLM suggestion, token count, 
    and status fields.
    """
    
    @given(title=st.text(min_size=1, max_size=100))
    @hypothesis_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_active_topic_has_required_fields(self, test_db, title):
        """Test that active topics have all required fields."""
        service = TopicService(test_db)
        
        # Close any existing active topics to ensure clean state
        existing_active = service.get_active_topic()
        if existing_active:
            service.close_topic(existing_active.id)
        
        # Create an active topic
        created_topic = service.create_topic(title=title)
        
        # Query active topic
        active_topic = service.get_active_topic()
        
        # Verify topic is returned and has required fields
        assert active_topic is not None
        assert active_topic.id == created_topic.id
        assert active_topic.title == title
        assert hasattr(active_topic, 'summary')
        assert hasattr(active_topic, 'llm_suggestion')
        assert hasattr(active_topic, 'token_count_since_summary')
        assert hasattr(active_topic, 'status')
        assert active_topic.status in ['active', 'closing_pending']
    
    def test_closing_pending_topic_returned_as_active(self, test_db):
        """Test that closing_pending topics are returned by get_active_topic."""
        service = TopicService(test_db)
        
        # Create topic and set to closing_pending
        topic = service.create_topic(title="Test Topic")
        service.record_close_request(topic.id, "agent_a")
        
        # Verify closing_pending topic is returned
        active_topic = service.get_active_topic()
        assert active_topic is not None
        assert active_topic.id == topic.id
        assert active_topic.status == "closing_pending"


# Property 19: Both agents must agree to close
class TestProperty19BothAgentsMustAgreeToClose:
    """**Validates: Requirements 8.2, 8.3**
    
    Property 19: For any topic, only when agent_a_wants_close and 
    agent_b_wants_close are both true should the topic status become 'closed'.
    """
    
    @given(
        agent_a_id=agent_id_strategy(),
        agent_b_id=agent_id_strategy()
    )
    @hypothesis_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_single_agent_request_sets_closing_pending(self, test_db, agent_a_id, agent_b_id):
        """Test that single agent close request sets status to closing_pending."""
        # Skip if agents have same ID
        if agent_a_id == agent_b_id:
            return
        
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # First agent requests close
        result = service.record_close_request(topic.id, agent_a_id)
        
        # Verify status is closing_pending, not closed
        assert result.both_agreed is False
        assert result.status == "closing_pending"
        
        # Verify topic state
        test_db.refresh(topic)
        assert topic.status == "closing_pending"
        assert topic.agent_a_wants_close is True
        assert topic.agent_b_wants_close is False
        assert topic.closing_requested_by == agent_a_id
    
    @given(
        agent_a_id=agent_id_strategy(),
        agent_b_id=agent_id_strategy()
    )
    @hypothesis_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_both_agents_request_closes_topic(self, test_db, agent_a_id, agent_b_id):
        """Test that both agents agreeing closes the topic."""
        # Skip if agents have same ID
        if agent_a_id == agent_b_id:
            return
        
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # First agent requests close
        result1 = service.record_close_request(topic.id, agent_a_id)
        assert result1.both_agreed is False
        assert result1.status == "closing_pending"
        
        # Second agent requests close
        result2 = service.record_close_request(topic.id, agent_b_id)
        
        # Verify both agreed and topic is closed
        assert result2.both_agreed is True
        assert result2.status == "closed"
        
        # Verify topic state
        test_db.refresh(topic)
        assert topic.status == "closed"
        assert topic.agent_a_wants_close is True
        assert topic.agent_b_wants_close is True
    
    def test_same_agent_requesting_twice_no_change(self, test_db):
        """Test that same agent requesting close twice doesn't change state."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Agent requests close twice
        result1 = service.record_close_request(topic.id, "agent_a")
        result2 = service.record_close_request(topic.id, "agent_a")
        
        # Verify status remains closing_pending
        assert result1.both_agreed is False
        assert result2.both_agreed is False
        assert result2.status == "closing_pending"
        
        test_db.refresh(topic)
        assert topic.status == "closing_pending"


# Property 39: Timeout automatic close
class TestProperty39TimeoutAutomaticClose:
    """**Validates: Requirements 8.7**
    
    Property 39: For any topic in closing_pending status exceeding 
    Closing_Timeout (default 5 minutes), the system should automatically 
    set the status to closed.
    """
    
    def test_timeout_closes_pending_topic(self, test_db):
        """Test that topics exceeding timeout are automatically closed."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Set topic to closing_pending with old timestamp
        timeout_seconds = settings.closing_timeout
        old_time = datetime.utcnow() - timedelta(seconds=timeout_seconds + 60)
        
        topic.status = "closing_pending"
        topic.closing_requested_by = "agent_a"
        topic.closing_requested_at = old_time
        topic.agent_a_wants_close = True
        test_db.commit()
        
        # Check for timeouts
        closed_ids = service.check_closing_timeout()
        
        # Verify topic was closed
        assert topic.id in closed_ids
        test_db.refresh(topic)
        assert topic.status == "closed"
    
    def test_timeout_does_not_close_recent_pending_topic(self, test_db):
        """Test that recent closing_pending topics are not closed."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Set topic to closing_pending with recent timestamp
        recent_time = datetime.utcnow() - timedelta(seconds=60)
        
        topic.status = "closing_pending"
        topic.closing_requested_by = "agent_a"
        topic.closing_requested_at = recent_time
        topic.agent_a_wants_close = True
        test_db.commit()
        
        # Check for timeouts
        closed_ids = service.check_closing_timeout()
        
        # Verify topic was not closed
        assert topic.id not in closed_ids
        test_db.refresh(topic)
        assert topic.status == "closing_pending"
    
    @given(timeout_offset=st.integers(min_value=1, max_value=3600))
    @hypothesis_settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_timeout_boundary_conditions(self, test_db, timeout_offset):
        """Test timeout behavior at various time offsets."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Set topic to closing_pending with specific offset
        timeout_seconds = settings.closing_timeout
        request_time = datetime.utcnow() - timedelta(seconds=timeout_offset)
        
        topic.status = "closing_pending"
        topic.closing_requested_by = "agent_a"
        topic.closing_requested_at = request_time
        topic.agent_a_wants_close = True
        test_db.commit()
        
        # Check for timeouts
        closed_ids = service.check_closing_timeout()
        
        # Verify correct behavior based on timeout
        test_db.refresh(topic)
        if timeout_offset > timeout_seconds:
            assert topic.id in closed_ids
            assert topic.status == "closed"
        else:
            assert topic.id not in closed_ids
            assert topic.status == "closing_pending"


# Property 40: Cancel close request
class TestProperty40CancelCloseRequest:
    """**Validates: Requirements 8.8, 8.9**
    
    Property 40: For any agent that initiated a close request, they should be 
    able to cancel the request before the other agent responds, reverting the 
    topic status to active.
    """
    
    @given(agent_id=agent_id_strategy())
    @hypothesis_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_cancel_close_request_reverts_to_active(self, test_db, agent_id):
        """Test that canceling close request reverts topic to active."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Agent requests close
        service.record_close_request(topic.id, agent_id)
        test_db.refresh(topic)
        assert topic.status == "closing_pending"
        
        # Agent cancels request
        service.cancel_close_request(topic.id, agent_id)
        
        # Verify topic is back to active
        test_db.refresh(topic)
        assert topic.status == "active"
        assert topic.agent_a_wants_close is False
        assert topic.agent_b_wants_close is False
        assert topic.closing_requested_by is None
        assert topic.closing_requested_at is None
    
    def test_cancel_by_non_requester_raises_error(self, test_db):
        """Test that non-requester cannot cancel close request."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Agent A requests close
        service.record_close_request(topic.id, "agent_a")
        
        # Agent B tries to cancel - should raise error
        with pytest.raises(ValueError, match="did not request close"):
            service.cancel_close_request(topic.id, "agent_b")
        
        # Verify topic still in closing_pending
        test_db.refresh(topic)
        assert topic.status == "closing_pending"
    
    def test_cancel_on_nonexistent_topic_raises_error(self, test_db):
        """Test that canceling on non-existent topic raises error."""
        service = TopicService(test_db)
        
        with pytest.raises(ValueError, match="not found"):
            service.cancel_close_request("nonexistent-id", "agent_a")


# Property 41: Closing status detailed information
class TestProperty41ClosingStatusDetailedInformation:
    """**Validates: Requirements 8.10**
    
    Property 41: For any topic in closing_pending status, the query API should 
    return requester, request time, and remaining timeout time.
    """
    
    @given(agent_id=agent_id_strategy())
    @hypothesis_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_closing_status_includes_all_details(self, test_db, agent_id):
        """Test that closing status includes all required details."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Request close
        service.record_close_request(topic.id, agent_id)
        
        # Get closing status
        status = service.get_closing_status(topic.id)
        
        # Verify all details are present
        assert status.status == "closing_pending"
        assert status.closing_requested_by == agent_id
        assert status.closing_requested_at is not None
        assert status.remaining_timeout_seconds is not None
        assert status.remaining_timeout_seconds >= 0
        assert status.remaining_timeout_seconds <= settings.closing_timeout
    
    def test_active_topic_status_has_no_closing_details(self, test_db):
        """Test that active topics have no closing details."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Get status for active topic
        status = service.get_closing_status(topic.id)
        
        # Verify no closing details
        assert status.status == "active"
        assert status.closing_requested_by is None
        assert status.closing_requested_at is None
        assert status.remaining_timeout_seconds is None
    
    def test_remaining_timeout_decreases_over_time(self, test_db):
        """Test that remaining timeout decreases as time passes."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Request close
        service.record_close_request(topic.id, "agent_a")
        
        # Get initial status
        status1 = service.get_closing_status(topic.id)
        initial_remaining = status1.remaining_timeout_seconds
        
        # Manually adjust the request time to simulate time passing
        test_db.refresh(topic)
        topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=10)
        test_db.commit()
        
        # Get updated status
        status2 = service.get_closing_status(topic.id)
        updated_remaining = status2.remaining_timeout_seconds
        
        # Verify remaining time decreased
        assert updated_remaining < initial_remaining
    
    def test_status_to_dict_serialization(self, test_db):
        """Test that ClosingStatusDetail can be serialized to dict."""
        service = TopicService(test_db)
        topic = service.create_topic(title="Test Topic")
        
        # Request close
        service.record_close_request(topic.id, "agent_a")
        
        # Get status and convert to dict
        status = service.get_closing_status(topic.id)
        status_dict = status.to_dict()
        
        # Verify dict structure
        assert isinstance(status_dict, dict)
        assert "status" in status_dict
        assert "closing_requested_by" in status_dict
        assert "closing_requested_at" in status_dict
        assert "remaining_timeout_seconds" in status_dict
        assert status_dict["status"] == "closing_pending"
