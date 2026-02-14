"""Queue service for managing asynchronous summary tasks."""
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from models.models import SummaryJob
from workers.celery_app import celery_app


class QueueService:
    """
    Service for managing asynchronous summary job queue.
    
    This service handles:
    - Enqueueing summary jobs to Celery
    - Querying job status
    - Retrieving pending jobs for workers
    """
    
    def __init__(self, db: Session):
        """
        Initialize QueueService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def enqueue_summary_job(
        self, 
        topic_id: str, 
        start_message_id: Optional[str], 
        end_message_id: str
    ) -> str:
        """
        Create a summary job and push it to the Celery queue.
        
        Args:
            topic_id: ID of the topic to summarize
            start_message_id: ID of the starting message (last summarized message)
            end_message_id: ID of the ending message (latest message)
        
        Returns:
            str: The job ID
        
        Validates:
            - Requirements 6.1, 6.9, 6.13
        """
        # Create job record in database
        job_id = str(uuid.uuid4())
        job = SummaryJob(
            id=job_id,
            topic_id=topic_id,
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            status="pending",
            retry_count=0
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Push to Celery queue
        # The task will be processed by workers asynchronously
        celery_app.send_task(
            "workers.tasks.process_summary_job",
            args=[job_id],
            queue="summary_jobs"
        )
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Query the status of a summary job.
        
        Args:
            job_id: The ID of the job to query
        
        Returns:
            dict: Job status information including:
                - id: Job ID
                - topic_id: Topic ID
                - status: Current status (pending/processing/done/failed)
                - retry_count: Number of retries
                - error_message: Error message if failed
                - created_at: Creation timestamp
                - updated_at: Last update timestamp
            None if job not found
        
        Validates:
            - Requirements 6.1, 6.9
        """
        job = self.db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        
        if not job:
            return None
        
        return {
            "id": job.id,
            "topic_id": job.topic_id,
            "status": job.status,
            "retry_count": job.retry_count,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }
    
    def get_pending_jobs(self, limit: int = 5) -> List[SummaryJob]:
        """
        Get pending summary jobs for worker processing.
        
        This method retrieves jobs with status='pending' ordered by creation time.
        The limit parameter helps control concurrency - workers should not pull
        more than the configured maximum concurrent tasks.
        
        Args:
            limit: Maximum number of jobs to retrieve (default 5, matches concurrency limit)
        
        Returns:
            List[SummaryJob]: List of pending jobs
        
        Validates:
            - Requirements 6.1, 6.13 (concurrent control)
        
        Note:
            The actual concurrency control is enforced by Celery's worker_concurrency
            setting. This method provides a way to query pending jobs for monitoring
            or manual processing.
        """
        jobs = (
            self.db.query(SummaryJob)
            .filter(SummaryJob.status == "pending")
            .order_by(SummaryJob.created_at.asc())
            .limit(limit)
            .all()
        )
        
        return jobs
    
    def get_jobs_by_topic(self, topic_id: str) -> List[SummaryJob]:
        """
        Get all summary jobs for a specific topic.
        
        Args:
            topic_id: The topic ID
        
        Returns:
            List[SummaryJob]: List of jobs for the topic, ordered by creation time
        """
        jobs = (
            self.db.query(SummaryJob)
            .filter(SummaryJob.topic_id == topic_id)
            .order_by(SummaryJob.created_at.desc())
            .all()
        )
        
        return jobs
    
    def update_job_status(
        self, 
        job_id: str, 
        status: str, 
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None
    ) -> bool:
        """
        Update the status of a summary job.
        
        This method is typically called by workers to update job progress.
        
        Args:
            job_id: The job ID
            status: New status (pending/processing/done/failed)
            error_message: Error message if status is failed
            retry_count: Updated retry count
        
        Returns:
            bool: True if update successful, False if job not found
        """
        job = self.db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        
        if not job:
            return False
        
        job.status = status
        if error_message is not None:
            job.error_message = error_message
        if retry_count is not None:
            job.retry_count = retry_count
        
        self.db.commit()
        return True
