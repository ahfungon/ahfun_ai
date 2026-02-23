"""Celery application configuration."""
from celery import Celery
from celery.signals import worker_process_init
from config.settings import settings
from utils.logging_config import setup_logging
from workers.celery_beat_config import beat_schedule

# Create Celery application
celery_app = Celery(
    "dual_agent_chat",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"]
)

# Initialize structured logging for Celery workers
@worker_process_init.connect
def init_worker_logging(**kwargs):
    """Initialize structured logging when worker process starts."""
    setup_logging(log_level="INFO")

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
    # Periodic task schedule
    beat_schedule=beat_schedule,
)

# Set concurrency limit (maximum 5 concurrent tasks as per requirements)
celery_app.conf.worker_concurrency = settings.celery_max_concurrent_tasks
