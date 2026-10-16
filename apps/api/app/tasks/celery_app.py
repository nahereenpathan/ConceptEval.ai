"""
Celery Distributed Task Queue Application Configuration
Initializes the Celery instance with Redis broker and result backend.
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "concept_eval_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=120,
    task_soft_time_limit=90,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_publish_retry=True,
    task_publish_retry_policy={
        "max_retries": 2,
        "interval_start": 0.1,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
