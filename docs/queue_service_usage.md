# QueueService Usage Guide

## Overview

The `QueueService` manages asynchronous summary job queue using Celery and Redis. It provides methods to enqueue summary jobs, query job status, and retrieve pending jobs for worker processing.

## Key Features

- **Asynchronous Processing**: Summary jobs are processed asynchronously by Celery workers
- **Concurrency Control**: Maximum 5 concurrent tasks (configurable via `CELERY_MAX_CONCURRENT_TASKS`)
- **Task Routing**: Summary jobs are routed to the `summary_jobs` queue
- **Job Status Tracking**: Query job status and retrieve pending jobs

## Requirements Validation

The QueueService validates the following requirements:
- **Requirement 6.1**: Trigger asynchronous SummaryJob when token threshold is reached
- **Requirement 6.9**: SummaryJob executes asynchronously without blocking message submission
- **Requirement 6.13**: Task queue manages execution order with maximum 5 concurrent tasks

## Basic Usage

### Initialize QueueService

```python
from sqlalchemy.orm import Session
from services.queue_service import QueueService

# Create service with database session
queue_service = QueueService(db_session)
```

### Enqueue a Summary Job

```python
# Enqueue a new summary job
job_id = queue_service.enqueue_summary_job(
    topic_id="topic-123",
    start_message_id="msg-100",  # Last summarized message (None for first summary)
    end_message_id="msg-200"     # Latest message
)

print(f"Job enqueued with ID: {job_id}")
```

### Query Job Status

```python
# Get job status
status = queue_service.get_job_status(job_id)

if status:
    print(f"Job Status: {status['status']}")
    print(f"Retry Count: {status['retry_count']}")
    if status['error_message']:
        print(f"Error: {status['error_message']}")
else:
    print("Job not found")
```

### Get Pending Jobs

```python
# Get pending jobs (for monitoring or manual processing)
pending_jobs = queue_service.get_pending_jobs(limit=5)

for job in pending_jobs:
    print(f"Job {job.id} for topic {job.topic_id}")
```

### Get Jobs by Topic

```python
# Get all jobs for a specific topic
topic_jobs = queue_service.get_jobs_by_topic("topic-123")

for job in topic_jobs:
    print(f"Job {job.id}: {job.status}")
```

### Update Job Status (Worker Use)

```python
# Workers use this to update job progress
success = queue_service.update_job_status(
    job_id=job_id,
    status="processing"
)

# Update with error message on failure
success = queue_service.update_job_status(
    job_id=job_id,
    status="failed",
    error_message="LLM API timeout",
    retry_count=1
)
```

## Job Status Values

- `pending`: Job is waiting to be processed
- `processing`: Job is currently being processed by a worker
- `done`: Job completed successfully
- `failed`: Job failed after all retries

## Celery Configuration

The QueueService integrates with Celery using the following configuration:

```python
# Task routing
task_routes = {
    "workers.tasks.process_summary_job": {"queue": "summary_jobs"},
}

# Concurrency limit (max 5 concurrent tasks)
worker_concurrency = 5

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
task_acks_late = True
task_reject_on_worker_lost = True
```

## Starting Celery Worker

To process summary jobs, start a Celery worker:

```bash
# Start worker for summary_jobs queue
celery -A workers.celery_app worker --loglevel=info --queue=summary_jobs

# Or start worker for all queues
celery -A workers.celery_app worker --loglevel=info
```

## Integration with MessageService

The QueueService is typically called by MessageService when token threshold is reached:

```python
# In MessageService.create_message()
if new_token_count >= threshold and not topic.pending_summary_job:
    # Mark topic as having pending job
    topic.pending_summary_job = True
    db.commit()
    
    # Enqueue summary job
    queue_service.enqueue_summary_job(
        topic_id=topic.id,
        start_message_id=topic.last_summarized_message_id,
        end_message_id=message.id
    )
```

## Error Handling

The QueueService handles errors gracefully:

- **Job not found**: Returns `None` or `False` depending on the method
- **Database errors**: Raises exceptions that should be caught by the caller
- **Celery connection errors**: Logged but job record is still created in database

## Testing

Run the QueueService tests:

```bash
# Run all QueueService tests
pytest tests/test_queue_service.py -v

# Run specific test
pytest tests/test_queue_service.py::TestQueueService::test_enqueue_summary_job_creates_job_record -v
```

## Monitoring

Monitor queue status:

```python
# Get pending jobs count
pending_count = len(queue_service.get_pending_jobs(limit=100))
print(f"Pending jobs: {pending_count}")

# Check specific topic's jobs
topic_jobs = queue_service.get_jobs_by_topic("topic-123")
failed_jobs = [j for j in topic_jobs if j.status == "failed"]
print(f"Failed jobs for topic: {len(failed_jobs)}")
```

## Best Practices

1. **Always use database transactions** when enqueueing jobs to ensure consistency
2. **Monitor pending job count** to detect queue backlogs
3. **Set appropriate concurrency limits** based on available resources
4. **Handle job failures gracefully** with retry mechanisms
5. **Log all job state changes** for debugging and auditing
