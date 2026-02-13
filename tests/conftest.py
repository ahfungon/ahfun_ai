"""Pytest configuration and fixtures for database model tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import Topic, Message, Agent, SummaryJob, SummaryHistory, AuditLog


@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test function."""
    # Use in-memory SQLite for fast tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def sample_topic(test_db):
    """Create a sample topic for testing."""
    from uuid import uuid4
    
    topic = Topic(
        id=str(uuid4()),
        title="Test Topic",
        status="active",
        summary="",
        token_count_since_summary=0,
        pending_summary_job=False,
        agent_a_wants_close=False,
        agent_b_wants_close=False
    )
    test_db.add(topic)
    test_db.commit()
    test_db.refresh(topic)
    
    return topic


@pytest.fixture(scope="function")
def sample_agent(test_db):
    """Create a sample agent for testing."""
    from uuid import uuid4
    import bcrypt
    
    agent = Agent(
        id=str(uuid4()),
        name="Test Agent",
        auth_token_hash=bcrypt.hashpw(b"test_token", bcrypt.gensalt()).decode()
    )
    test_db.add(agent)
    test_db.commit()
    test_db.refresh(agent)
    
    return agent
