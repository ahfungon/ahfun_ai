# Celery Beat Periodic Tasks

This document explains how to run and manage periodic tasks using Celery Beat.

## Overview

The system uses Celery Beat to schedule periodic tasks that run automatically at specified intervals. Currently, the following periodic tasks are configured:

1. **check_closing_timeouts** - Runs every minute to check for topics in `closing_pending` state that have exceeded the timeout threshold and automatically closes them.

## Running Celery Beat

### Prerequisites

- Redis server must be running (default: `redis://localhost:6379/0`)
- Database must be initialized
- Environment variables configured in `.env` file

### Starting Celery Beat

To start the Celery Beat scheduler:

```bash
celery -A workers.celery_app beat --loglevel=info
```

This will start the scheduler that triggers periodic tasks according to the configured schedule.

### Starting Celery Workers

In addition to the Beat scheduler, you need to run Celery workers to execute the tasks:

```bash
celery -A workers.celery_app worker --loglevel=info --queues=periodic_tasks,summary_jobs,default
```

### Running Both Together

For development, you can run both the worker and beat scheduler in a single process:

```bash
celery -A workers.celery_app worker --beat --loglevel=info --queues=periodic_tasks,summary_jobs,default
```

**Note:** In production, it's recommended to run the beat scheduler and workers as separate processes.

## Periodic Task Configuration

### check_closing_timeouts

**Schedule:** Every 60 seconds (1 minute)

**Purpose:** Automatically closes topics that have been in `closing_pending` state for longer than the configured timeout period.

**Configuration:**
- Timeout period: Configured via `CLOSING_TIMEOUT` environment variable (default: 300 seconds / 5 minutes)
- Queue: `periodic_tasks`

**Behavior:**
1. Queries all topics with `status=closing_pending`
2. Checks if `closing_requested_at + timeout > now`
3. Closes timed-out topics by setting `status=closed`
4. Records audit log for each timeout closure

**Audit Log Details:**
- Operation type: `status_changed`
- Reason: `closing_timeout`
- Old status: `closing_pending`
- New status: `closed`
- Timeout seconds: Value from configuration

## Configuration

### Beat Schedule

The periodic task schedule is defined in `workers/celery_beat_config.py`:

```python
beat_schedule = {
    'check-closing-timeouts': {
        'task': 'workers.tasks.check_closing_timeouts',
        'schedule': 60.0,  # Run every 60 seconds
        'options': {
            'queue': 'periodic_tasks',
        }
    },
}
```

### Modifying the Schedule

To change the frequency of the timeout check:

1. Edit `workers/celery_beat_config.py`
2. Modify the `schedule` value (in seconds)
3. Restart the Celery Beat scheduler

Example - Run every 30 seconds:
```python
'schedule': 30.0,
```

Example - Run every 5 minutes:
```python
'schedule': 300.0,
```

### Using Crontab Schedule

For more complex schedules, you can use crontab syntax:

```python
from celery.schedules import crontab

beat_schedule = {
    'check-closing-timeouts': {
        'task': 'workers.tasks.check_closing_timeouts',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {
            'queue': 'periodic_tasks',
        }
    },
}
```

## Monitoring

### Checking Task Execution

To monitor periodic task execution, check the Celery worker logs:

```bash
celery -A workers.celery_app worker --loglevel=info
```

Look for log entries like:
```
[INFO] Starting closing timeout check
[INFO] Topic <topic_id> closed due to timeout
[INFO] Closed 2 topics due to timeout
```

### Viewing Audit Logs

Timeout closures are recorded in the `audit_logs` table. Query them using:

```sql
SELECT * FROM audit_logs 
WHERE operation_type = 'status_changed' 
AND details LIKE '%closing_timeout%'
ORDER BY created_at DESC;
```

## Troubleshooting

### Beat Scheduler Not Running

**Symptom:** Periodic tasks are not executing

**Solution:**
1. Check if Celery Beat is running: `ps aux | grep celery`
2. Verify Redis connection: `redis-cli ping`
3. Check Beat scheduler logs for errors

### Tasks Not Executing

**Symptom:** Beat scheduler is running but tasks don't execute

**Solution:**
1. Ensure Celery workers are running
2. Verify workers are listening to the `periodic_tasks` queue
3. Check worker logs for errors

### Database Connection Issues

**Symptom:** Tasks fail with database errors

**Solution:**
1. Verify database connection string in `.env`
2. Check database is accessible
3. Ensure database schema is up to date

## Production Deployment

### Recommended Setup

1. **Run Beat Scheduler as a separate process:**
   ```bash
   celery -A workers.celery_app beat --loglevel=info
   ```

2. **Run multiple workers for redundancy:**
   ```bash
   celery -A workers.celery_app worker --loglevel=info --concurrency=4 --queues=periodic_tasks,summary_jobs,default
   ```

3. **Use a process manager (systemd, supervisor, etc.):**
   - Ensures processes restart on failure
   - Manages logs
   - Provides monitoring

### Example Systemd Service Files

**celery-beat.service:**
```ini
[Unit]
Description=Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/celery -A workers.celery_app beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

**celery-worker.service:**
```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/celery -A workers.celery_app worker --loglevel=info --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
```

## Testing

### Manual Testing

To manually trigger the timeout check task:

```python
from workers.tasks import check_closing_timeouts

# Run synchronously for testing
result = check_closing_timeouts()
print(f"Closed {result['closed_count']} topics")
print(f"Topic IDs: {result['closed_topic_ids']}")
```

### Unit Tests

Run the unit tests for the timeout check task:

```bash
python -m pytest tests/test_closing_timeout_task.py -v
```

## Related Documentation

- [Queue Service Usage](queue_service_usage.md) - Information about the task queue system
- [Requirements Document](../.kiro/specs/dual-agent-chat/requirements.md) - Requirement 8.7 (Closing Timeout)
- [Design Document](../.kiro/specs/dual-agent-chat/design.md) - Timeout check implementation details
