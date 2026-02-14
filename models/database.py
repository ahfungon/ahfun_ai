"""Database connection and session management."""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config.settings import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_pre_ping=True,
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction(db: Session):
    """
    Context manager for database transactions with automatic commit/rollback.
    
    This ensures atomic operations and proper error handling:
    - Commits on successful completion
    - Rolls back on any exception
    - Provides isolation for concurrent operations
    
    Usage:
        with transaction(db):
            # Perform database operations
            topic.token_count += 10
            # Automatically commits on exit
    
    Args:
        db: Database session
        
    Yields:
        Database session
        
    Validates:
        Requirements 10.1, 10.2, 10.3, 10.4, 10.5
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


@contextmanager
def atomic_update(db: Session, model_class, record_id: str):
    """
    Context manager for atomic updates with row-level locking.
    
    This acquires a row-level lock (SELECT FOR UPDATE) to prevent
    concurrent modifications and ensures atomic updates.
    
    Usage:
        with atomic_update(db, Topic, topic_id) as topic:
            topic.token_count += 10
            # Automatically commits with lock held
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class
        record_id: ID of the record to lock
        
    Yields:
        Locked model instance
        
    Raises:
        ValueError: If record not found
        
    Validates:
        Requirements 10.1, 10.2, 10.3, 10.5
    """
    try:
        # Acquire row-level lock
        record = db.query(model_class).filter(
            model_class.id == record_id
        ).with_for_update().first()
        
        if not record:
            raise ValueError(f"{model_class.__name__} {record_id} not found")
        
        yield record
        db.commit()
    except Exception:
        db.rollback()
        raise
