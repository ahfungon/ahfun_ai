"""Celery tasks for background processing."""
from workers.celery_app import celery_app


@celery_app.task(name="workers.tasks.process_summary_job")
def process_summary_job(job_id: str):
    """
    Process a summary job asynchronously.
    
    This task will be implemented in later tasks.
    
    Args:
        job_id: The ID of the summary job to process
    """
    # Implementation will be added in Task 10
    pass


@celery_app.task(name="workers.tasks.check_closing_timeouts")
def check_closing_timeouts():
    """
    Periodic task to check for closing_pending topics that have timed out.
    
    This task will be implemented in later tasks.
    """
    # Implementation will be added in Task 13
    pass
