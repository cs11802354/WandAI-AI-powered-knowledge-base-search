"""
Celery configuration for background task processing.
Celery handles long-running tasks like document processing.
"""

from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "knowledge_base",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.document_tasks", "app.tasks.maintenance_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
)

# Scheduled tasks with Celery Beat
celery_app.conf.beat_schedule = {
    # Rebuild vector index every night at 2 AM
    "rebuild-index-nightly": {
        "task": "app.tasks.maintenance_tasks.rebuild_vector_index",
        "schedule": crontab(hour=2, minute=0),
    },
    # Clean up temp files every hour
    "cleanup-temp-files": {
        "task": "app.tasks.maintenance_tasks.cleanup_temp_files",
        "schedule": crontab(minute=0),
    },
}
