from celery import Celery
from app.core.config import settings

# Initialize Celery app with Redis as both the broker and the backend
celery_app = Celery(
    "pulseguard",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Load additional configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=["app.core.tasks"] # Explicitly import tasks to register them
)

# Periodic task configuration using Celery Beat schedule
# We run the orchestrator scheduler task every 10 seconds to detect due endpoints
celery_app.conf.beat_schedule = {
    "orchestrate-endpoint-checks-every-10-seconds": {
        "task": "app.core.tasks.scheduler_task",
        "schedule": 10.0, # Check every 10 seconds
    }
}
