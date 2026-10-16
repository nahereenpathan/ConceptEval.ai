"""
Background Tasks Package
Celery worker tasks for code evaluation and asynchronous orchestration.
"""

from app.tasks.celery_app import celery_app
from app.tasks.evaluation import evaluate_submission_task

__all__ = ["celery_app", "evaluate_submission_task"]
