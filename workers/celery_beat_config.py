"""Celery Beat periodic task configuration."""
from celery.schedules import crontab

# Periodic task schedule configuration
beat_schedule = {
    # Check closing timeouts every minute
    'check-closing-timeouts': {
        'task': 'workers.tasks.check_closing_timeouts',
        'schedule': 60.0,  # Run every 60 seconds (1 minute)
        'options': {
            'queue': 'periodic_tasks',
        }
    },
}
