"""Celery Beat periodic task configuration."""
from celery.schedules import crontab

# Periodic task schedule configuration
# Note: Closing timeout feature has been removed.
# Topics now require explicit agreement from both agents to close.
beat_schedule = {
    # No periodic tasks currently configured
}
