from celery import Celery
from app.core.config import settings

from app.core.redis_client import redis_available

# Determine broker and backend URL (fallback to in-memory if Redis is offline)
broker_url = settings.REDIS_URL if redis_available else "memory://"
backend_url = settings.REDIS_URL if redis_available else "cache+memory://"

# Initialize Celery app
celery_app = Celery(
    "pulseguard",
    broker=broker_url,
    backend=backend_url
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
