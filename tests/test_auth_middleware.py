"""Tests for AuthMiddleware."""
import bcrypt
import pytest
from unittest.mock import Mock
from fastapi import Request
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth_middleware import AuthMiddleware
from api.exceptions import AuthenticationError
from models.models import Agent
from models.database import Base


class TestAuthMiddleware:
    """Test suite for AuthMiddleware authentication."""
    
    def test_successful_authentication(self, test_db):
        """Test successful authentication with valid credentials."""
        # Create test agent with hashed token
        test_token = "test-token-123"
        hashed_token = bcrypt.hashpw(test_token.encode('utf-8'), bcrypt.gensalt())
        
        agent = Agent(
            id="agent-1",
            name="Test Agent",
            auth_token_hash=hashed_token.decode('utf-8')
        )
        test_db.add(agent)
        test_db.commit()
        
        # Create mock request with valid headers
        request = Mock(spec=Request)
        request.headers = {
            "X-Agent-Id": "agent-1",
            "X-Auth-Token": test_token
        }
        
        # Authenticate
        authenticated_agent = AuthMiddleware.authenticate(request, test_db)
        
        assert authenticated_agent.id == "agent-1"
        assert authenticated_agent.name == "Test Agent"
    
    def test_missing_agent_id_header(self, test_db):
        """Test authentication fails when X-Agent-Id header is missing."""
        request = Mock(spec=Request)
        request.headers = {
            "X-Auth-Token": "some-token"
        }
        
        with pytest.raises(AuthenticationError) as exc_info:
            AuthMiddleware.authenticate(request, test_db)
        
        assert "Missing X-Agent-Id header" in str(exc_info.value)
    
    def test_missing_auth_token_header(self, test_db):
        """Test authentication fails when X-Auth-Token header is missing."""
        request = Mock(spec=Request)
        request.headers = {
            "X-Agent-Id": "agent-1"
        }
        
        with pytest.raises(AuthenticationError) as exc_info:
            AuthMiddleware.authenticate(request, test_db)
        
        assert "Missing X-Auth-Token header" in str(exc_info.value)
    
    def test_agent_not_found(self, test_db):
        """Test authentication fails when agent_id doesn't exist."""
        request = Mock(spec=Request)
        request.headers = {
            "X-Agent-Id": "non-existent-agent",
            "X-Auth-Token": "some-token"
        }
        
        with pytest.raises(AuthenticationError) as exc_info:
            AuthMiddleware.authenticate(request, test_db)
        
        assert "not found" in str(exc_info.value)
    
    def test_invalid_token(self, test_db):
        """Test authentication fails with incorrect token."""
        # Create test agent with hashed token
        correct_token = "correct-token"
        hashed_token = bcrypt.hashpw(correct_token.encode('utf-8'), bcrypt.gensalt())
        
        agent = Agent(
            id="agent-2",
            name="Test Agent 2",
            auth_token_hash=hashed_token.decode('utf-8')
        )
        test_db.add(agent)
        test_db.commit()
        
        # Try to authenticate with wrong token
        request = Mock(spec=Request)
        request.headers = {
            "X-Agent-Id": "agent-2",
            "X-Auth-Token": "wrong-token"
        }
        
        with pytest.raises(AuthenticationError) as exc_info:
            AuthMiddleware.authenticate(request, test_db)
        
        assert "Invalid authentication token" in str(exc_info.value)
    
    def test_token_hash_verification(self, test_db):
        """Test that bcrypt hash verification works correctly."""
        # Create multiple agents with different tokens
        tokens = ["token-a", "token-b", "token-c"]
        
        for i, token in enumerate(tokens):
            hashed = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt())
            agent = Agent(
                id=f"agent-{i}",
                name=f"Agent {i}",
                auth_token_hash=hashed.decode('utf-8')
            )
            test_db.add(agent)
        
        test_db.commit()
        
        # Verify each token works only for its corresponding agent
        for i, token in enumerate(tokens):
            request = Mock(spec=Request)
            request.headers = {
                "X-Agent-Id": f"agent-{i}",
                "X-Auth-Token": token
            }
            
            authenticated = AuthMiddleware.authenticate(request, test_db)
            assert authenticated.id == f"agent-{i}"
    
    def test_empty_headers(self, test_db):
        """Test authentication fails with empty header values."""
        # Test empty agent_id
        request = Mock(spec=Request)
        request.headers = {
            "X-Agent-Id": "",
            "X-Auth-Token": "some-token"
        }
        
        with pytest.raises(AuthenticationError):
            AuthMiddleware.authenticate(request, test_db)
        
        # Test empty token
        request.headers = {
            "X-Agent-Id": "agent-1",
            "X-Auth-Token": ""
        }
        
        with pytest.raises(AuthenticationError):
            AuthMiddleware.authenticate(request, test_db)


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

class TestAuthMiddlewareProperties:
    """Property-based tests for AuthMiddleware using Hypothesis."""
    
    def _create_test_db(self):
        """Create a fresh test database session."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        TestSessionLocal = sessionmaker(bind=engine)
        return TestSessionLocal()
    
    # Feature: dual-agent-chat, Property 5: 认证失败返回401
    # Validates: Requirements 2.3, 12.2
    @given(
        agent_id=st.text(min_size=1, max_size=50),
        token=st.text(min_size=8, max_size=64)
    )
    @settings(max_examples=100)
    def test_property_missing_headers_fails(self, agent_id, token):
        """
        **Validates: Requirements 2.3, 12.2**
        
        Property: For any request missing X-Agent-Id or X-Auth-Token headers,
        authentication must fail with AuthenticationError.
        """
        test_db = self._create_test_db()
        
        try:
            # Test missing X-Agent-Id
            request = Mock(spec=Request)
            request.headers = {
                "X-Auth-Token": token
            }
            
            with pytest.raises(AuthenticationError) as exc_info:
                AuthMiddleware.authenticate(request, test_db)
            
            assert "Missing X-Agent-Id header" in str(exc_info.value)
            
            # Test missing X-Auth-Token
            request.headers = {
                "X-Agent-Id": agent_id
            }
            
            with pytest.raises(AuthenticationError) as exc_info:
                AuthMiddleware.authenticate(request, test_db)
            
            assert "Missing X-Auth-Token header" in str(exc_info.value)
        finally:
            test_db.close()
    
    # Feature: dual-agent-chat, Property 5: 认证失败返回401
    # Validates: Requirements 2.3, 12.2
    @given(
        agent_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        token=st.text(min_size=8, max_size=64)
    )
    @settings(max_examples=100)
    def test_property_invalid_agent_id_fails(self, agent_id, token):
        """
        **Validates: Requirements 2.3, 12.2**
        
        Property: For any request with a non-existent agent_id,
        authentication must fail with AuthenticationError.
        """
        test_db = self._create_test_db()
        
        try:
            request = Mock(spec=Request)
            request.headers = {
                "X-Agent-Id": agent_id,
                "X-Auth-Token": token
            }
            
            with pytest.raises(AuthenticationError) as exc_info:
                AuthMiddleware.authenticate(request, test_db)
            
            assert "not found" in str(exc_info.value)
        finally:
            test_db.close()
    
    # Feature: dual-agent-chat, Property 5: 认证失败返回401
    # Validates: Requirements 2.3, 12.2
    @given(
        agent_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        correct_token=st.text(min_size=8, max_size=64),
        wrong_token=st.text(min_size=8, max_size=64)
    )
    @settings(
        max_examples=20,  # Reduced from 100 due to bcrypt performance
        suppress_health_check=[HealthCheck.too_slow]
    )
    def test_property_invalid_token_fails(self, agent_id, correct_token, wrong_token):
        """
        **Validates: Requirements 2.3, 12.2**
        
        Property: For any agent with a valid token, authentication with
        a different token must fail with AuthenticationError.
        """
        # Skip if tokens are the same
        if correct_token == wrong_token:
            return
        
        test_db = self._create_test_db()
        
        try:
            # Create agent with correct token (use faster bcrypt rounds for testing)
            hashed_token = bcrypt.hashpw(correct_token.encode('utf-8'), bcrypt.gensalt(rounds=4))
            agent = Agent(
                id=agent_id,
                name=f"Agent {agent_id}",
                auth_token_hash=hashed_token.decode('utf-8')
            )
            test_db.add(agent)
            test_db.commit()
            
            # Try to authenticate with wrong token
            request = Mock(spec=Request)
            request.headers = {
                "X-Agent-Id": agent_id,
                "X-Auth-Token": wrong_token
            }
            
            with pytest.raises(AuthenticationError) as exc_info:
                AuthMiddleware.authenticate(request, test_db)
            
            assert "Invalid authentication token" in str(exc_info.value)
        finally:
            test_db.close()
    
    # Feature: dual-agent-chat, Property 5: 认证失败返回401
    # Validates: Requirements 2.3, 12.2
    @given(
        agent_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        token=st.text(min_size=8, max_size=64)
    )
    @settings(
        max_examples=20,  # Reduced from 100 due to bcrypt performance
        suppress_health_check=[HealthCheck.too_slow]
    )
    def test_property_token_hash_verification(self, agent_id, token):
        """
        **Validates: Requirements 2.3, 12.2**
        
        Property: For any agent with a hashed token, authentication with
        the correct token must succeed and return the agent object.
        """
        test_db = self._create_test_db()
        
        try:
            # Create agent with hashed token (use faster bcrypt rounds for testing)
            hashed_token = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt(rounds=4))
            agent = Agent(
                id=agent_id,
                name=f"Agent {agent_id}",
                auth_token_hash=hashed_token.decode('utf-8')
            )
            test_db.add(agent)
            test_db.commit()
            
            # Authenticate with correct token
            request = Mock(spec=Request)
            request.headers = {
                "X-Agent-Id": agent_id,
                "X-Auth-Token": token
            }
            
            authenticated_agent = AuthMiddleware.authenticate(request, test_db)
            
            assert authenticated_agent.id == agent_id
            assert authenticated_agent.name == f"Agent {agent_id}"
            assert authenticated_agent.auth_token_hash == hashed_token.decode('utf-8')
        finally:
            test_db.close()
    
    # Feature: dual-agent-chat, Property 5: 认证失败返回401
    # Validates: Requirements 2.3, 12.2
    @given(
        agent_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        token=st.text(min_size=8, max_size=64)
    )
    @settings(max_examples=100)
    def test_property_empty_credentials_fail(self, agent_id, token):
        """
        **Validates: Requirements 2.3, 12.2**
        
        Property: For any request with empty agent_id or token,
        authentication must fail with AuthenticationError.
        """
        test_db = self._create_test_db()
        
        try:
            # Test empty agent_id
            request = Mock(spec=Request)
            request.headers = {
                "X-Agent-Id": "",
                "X-Auth-Token": token
            }
            
            with pytest.raises(AuthenticationError):
                AuthMiddleware.authenticate(request, test_db)
            
            # Test empty token
            request.headers = {
                "X-Agent-Id": agent_id,
                "X-Auth-Token": ""
            }
            
            with pytest.raises(AuthenticationError):
                AuthMiddleware.authenticate(request, test_db)
        finally:
            test_db.close()
