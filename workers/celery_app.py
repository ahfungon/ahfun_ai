"""Celery application configuration."""
from celery import Celery
from config.settings import settings

# Create Celery application
celery_app = Celery(
    "dual_agent_chat",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    # Task routing configuration
    task_routes={
        "workers.tasks.process_summary_job": {"queue": "summary_jobs"},
        "workers.tasks.check_closing_timeouts": {"queue": "periodic_tasks"},
    },
    # Default queue
    task_default_queue="default",
)

# Set concurrency limit (maximum 5 concurrent tasks as per requirements)
celery_app.conf.worker_concurrency = settings.celery_max_concurrent_tasks
