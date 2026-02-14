"""Celery tasks for background processing."""
import logging
import traceback
import time
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from workers.celery_app import celery_app
from models.database import SessionLocal, transaction, atomic_update
from models.models import SummaryJob, Topic, Message
from services.summary_service import SummaryService
from services.topic_service import TopicService
from config.settings import settings
from utils.logging_config import log_retry_attempt, log_error_with_context

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(name="workers.tasks.process_summary_job")
def process_summary_job(job_id: str, db_session: Optional[Session] = None):
    """
    Process a summary job asynchronously with exponential backoff retry mechanism.
    
    This task:
    1. Acquires database row lock on the topic (SELECT FOR UPDATE)
    2. Retrieves new messages since last_summarized_message_id
    3. Calls SummaryService.generate_summary() with try-except for LLM failures
    4. On failure: increments retry_count, implements exponential backoff
    5. After max retries: marks job as failed, releases pending_summary_job flag
    6. On success: saves summary history, updates topic, applies LLM suggestion
    7. Resets token_count_since_summary to 0
    8. Sets pending_summary_job to False
    9. Marks job as done
    
    Args:
        job_id: The ID of the summary job to process
        db_session: Optional database session (for testing)
    
    Validates:
        Requirements 6.1, 6.4, 6.5, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 6.14, 6.15, 7.5, 12.4, 12.7, 12.8
    """
    # Use provided session or create new one
    db: Session = db_session if db_session else SessionLocal()
    should_close_db = db_session is None  # Only close if we created it
    
    try:
        # 1. Get the job
        job = db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        if not job:
            log_error_with_context(
                logger,
                ValueError(f"Summary job {job_id} not found"),
                {"job_id": job_id},
                f"Summary job {job_id} not found"
            )
            return
        
        # Update job status to processing
        job.status = "processing"
        db.commit()
        
        logger.info(
            f"Processing summary job {job_id} for topic {job.topic_id} "
            f"(retry {job.retry_count}/{settings.max_retries})",
            extra={
                "event_type": "job_processing",
                "job_id": job_id,
                "topic_id": job.topic_id,
                "retry_count": job.retry_count,
                "max_retries": settings.max_retries
            }
        )
        
        # 2. Acquire row lock on topic (SELECT FOR UPDATE)
        # This prevents concurrent summary jobs on the same topic
        topic = db.query(Topic).filter(
            Topic.id == job.topic_id
        ).with_for_update().first()
        
        if not topic:
            error_msg = f"Topic {job.topic_id} not found"
            log_error_with_context(
                logger,
                ValueError(error_msg),
                {
                    "job_id": job_id,
                    "topic_id": job.topic_id
                },
                error_msg
            )
            job.status = "failed"
            job.error_message = error_msg
            db.commit()
            return
        
        # 3. Get new messages since last_summarized_message_id
        new_messages = _get_messages_since(
            db, 
            job.topic_id, 
            job.start_message_id
        )
        
        if not new_messages:
            logger.warning(
                f"No new messages found for job {job_id}",
                extra={
                    "event_type": "no_messages",
                    "job_id": job_id,
                    "topic_id": job.topic_id
                }
            )
            # Still mark as done, but don't update summary
            job.status = "done"
            topic.pending_summary_job = False
            db.commit()
            return
        
        logger.info(
            f"Found {len(new_messages)} new messages for job {job_id}",
            extra={
                "event_type": "messages_found",
                "job_id": job_id,
                "topic_id": job.topic_id,
                "message_count": len(new_messages)
            }
        )
        
        # 4. Initialize services
        summary_service = SummaryService(db)
        topic_service = TopicService(db)
        
        try:
            # 5. Generate summary (wrapped in try-except for LLM failures)
            result = summary_service.generate_summary(topic, new_messages)
            
            logger.info(
                f"Generated summary for job {job_id}: "
                f"suggestion={result.suggestion}, end_score={result.end_score}",
                extra={
                    "event_type": "summary_generated",
                    "job_id": job_id,
                    "topic_id": job.topic_id,
                    "suggestion": result.suggestion,
                    "end_score": result.end_score
                }
            )
            
            # Wrap all database updates in a single transaction for atomicity
            with transaction(db):
                # 6. Save summary history
                summary_service.save_summary_history(
                    topic_id=job.topic_id,
                    summary=result.summary,
                    suggestion=result.suggestion,
                    end_score=result.end_score
                )
                
                # 7. Update topic with new summary, suggestion, end_score
                # Only update suggestion if not in closing_pending (Requirement 7.8)
                if topic.status != "closing_pending":
                    summary_service.update_topic_summary(
                        topic_id=job.topic_id,
                        summary=result.summary,
                        suggestion=result.suggestion,
                        end_score=result.end_score
                    )
                else:
                    # In closing_pending, only update summary but keep old suggestion
                    summary_service.update_topic_summary(
                        topic_id=job.topic_id,
                        summary=result.summary,
                        suggestion=topic.llm_suggestion,  # Keep existing suggestion
                        end_score=topic.end_score  # Keep existing end_score
                    )
                
                # 8. Apply LLM suggestion (force_end logic)
                # This will be ignored if already in closing_pending (Requirement 7.8)
                summary_service.apply_llm_suggestion(topic, result.suggestion)
                
                # 9. Update topic state atomically
                topic.last_summarized_message_id = job.end_message_id
                topic.token_count_since_summary = 0
                topic.pending_summary_job = False
                
                # 10. Mark job as done
                job.status = "done"
                
                # Transaction commits here automatically
            
            logger.info(
                f"Successfully completed summary job {job_id}",
                extra={
                    "event_type": "job_completed",
                    "job_id": job_id,
                    "topic_id": job.topic_id,
                    "suggestion": result.suggestion,
                    "end_score": result.end_score
                }
            )
            
        except Exception as llm_error:
            # LLM call failed - implement retry mechanism with exponential backoff
            error_msg = str(llm_error)
            error_trace = traceback.format_exc()
            
            # Increment retry count
            job.retry_count += 1
            job.error_message = error_msg
            
            # Log detailed error information with structured data
            log_error_with_context(
                logger,
                llm_error,
                {
                    "event_type": "llm_failure",
                    "job_id": job_id,
                    "topic_id": job.topic_id,
                    "retry_count": job.retry_count,
                    "max_retries": settings.max_retries,
                    "traceback": error_trace
                },
                f"LLM call failed for summary job {job_id} (attempt {job.retry_count}/{settings.max_retries})"
            )
            
            # Check if we've exceeded max retries
            if job.retry_count >= settings.max_retries:
                # All retries exhausted - mark as failed and release lock
                job.status = "failed"
                topic.pending_summary_job = False
                
                log_retry_attempt(
                    logger,
                    job_id=job_id,
                    topic_id=job.topic_id,
                    retry_count=job.retry_count,
                    max_retries=settings.max_retries,
                    error=error_msg,
                    next_delay=None
                )
                
                db.commit()
                return
            else:
                # Retry with exponential backoff
                job.status = "pending"
                db.commit()
                
                # Get delay for this retry attempt (0-indexed)
                retry_delays = settings.retry_delays_list
                delay_index = min(job.retry_count - 1, len(retry_delays) - 1)
                delay = retry_delays[delay_index]
                
                log_retry_attempt(
                    logger,
                    job_id=job_id,
                    topic_id=job.topic_id,
                    retry_count=job.retry_count,
                    max_retries=settings.max_retries,
                    error=error_msg,
                    next_delay=delay
                )
                
                # Wait for exponential backoff delay
                time.sleep(delay)
                
                # Re-enqueue the job for retry
                process_summary_job.apply_async(args=[job_id], countdown=0)
                return
        
    except Exception as e:
        # Unexpected error (not LLM-related)
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        log_error_with_context(
            logger,
            e,
            {
                "event_type": "unexpected_error",
                "job_id": job_id,
                "traceback": error_trace
            },
            f"Unexpected error in summary job {job_id}"
        )
        
        # Update job with error information
        job = db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = f"Unexpected error: {error_msg}"
            
            # Release the lock on final failure
            topic = db.query(Topic).filter(Topic.id == job.topic_id).first()
            if topic:
                topic.pending_summary_job = False
            
            db.commit()
        
        # Don't re-raise for unexpected errors - just fail the job
        
    finally:
        if should_close_db:
            db.close()


def _get_messages_since(
    db: Session,
    topic_id: str,
    start_message_id: Optional[str]
) -> List[Message]:
    """
    Get all messages since a specific message ID.
    
    Args:
        db: Database session
        topic_id: Topic ID
        start_message_id: Starting message ID (exclusive), or None for all messages
    
    Returns:
        List of messages ordered by created_at ascending
    """
    query = db.query(Message).filter(Message.topic_id == topic_id)
    
    if start_message_id:
        # Get the timestamp of the start message
        start_message = db.query(Message).filter(
            Message.id == start_message_id
        ).first()
        
        if start_message:
            # Get messages created after the start message
            query = query.filter(Message.created_at > start_message.created_at)
    
    # Order by created_at ascending (oldest to newest)
    messages = query.order_by(Message.created_at.asc()).all()
    
    return messages


@celery_app.task(name="workers.tasks.check_closing_timeouts")
def check_closing_timeouts(db_session: Optional[Session] = None):
    """
    Periodic task to check for closing_pending topics that have timed out.
    
    This task runs every minute and:
    1. Queries all topics with status=closing_pending
    2. Checks if closing_requested_at + timeout > now
    3. Automatically closes timed-out topics
    4. Records audit log for each timeout closure
    
    Args:
        db_session: Optional database session (for testing)
    
    Validates:
        Requirements 8.7
    """
    # Use provided session or create new one
    db: Session = db_session if db_session else SessionLocal()
    should_close_db = db_session is None  # Only close if we created it
    
    try:
        logger.info(
            "Starting closing timeout check",
            extra={
                "event_type": "timeout_check_started"
            }
        )
        
        # Initialize services
        topic_service = TopicService(db)
        
        # Import AuditLogService here to avoid circular imports
        from services.audit_log_service import AuditLogService
        audit_log_service = AuditLogService(db)
        
        # Check for timed-out topics
        closed_topic_ids = topic_service.check_closing_timeout()
        
        # Record audit log for each closed topic
        for topic_id in closed_topic_ids:
            audit_log_service.record(
                operation_type=audit_log_service.OPERATION_STATUS_CHANGED,
                topic_id=topic_id,
                agent_id=None,  # System action, no specific agent
                details={
                    "reason": "closing_timeout",
                    "old_status": "closing_pending",
                    "new_status": "closed",
                    "timeout_seconds": settings.closing_timeout
                }
            )
            
            logger.info(
                f"Topic {topic_id} closed due to timeout",
                extra={
                    "event_type": "topic_timeout_closed",
                    "topic_id": topic_id,
                    "timeout_seconds": settings.closing_timeout
                }
            )
        
        if closed_topic_ids:
            logger.info(
                f"Closed {len(closed_topic_ids)} topics due to timeout",
                extra={
                    "event_type": "timeout_check_completed",
                    "closed_count": len(closed_topic_ids),
                    "closed_topic_ids": closed_topic_ids
                }
            )
        else:
            logger.debug(
                "No topics timed out",
                extra={
                    "event_type": "timeout_check_completed",
                    "closed_count": 0
                }
            )
        
        return {
            "closed_count": len(closed_topic_ids),
            "closed_topic_ids": closed_topic_ids
        }
        
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        log_error_with_context(
            logger,
            e,
            {
                "event_type": "timeout_check_error",
                "traceback": error_trace
            },
            "Error checking closing timeouts"
        )
        
        # Don't re-raise - log and continue
        return {
            "error": error_msg,
            "closed_count": 0,
            "closed_topic_ids": []
        }
        
    finally:
        if should_close_db:
            db.close()
