"""
SentraVision — Celery Application Definition and Configuration
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

# Initialize Celery app instance with broker and result backend URLs from Settings
celery_app = Celery(
    "sentravision",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Apply performance and reliability configurations for Celery workers
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    timezone="UTC",
    
    # Prefetch 1 task at a time per worker process to ensure fair distribution of heavy processing tasks
    worker_prefetch_multiplier=1,
    
    # Task acks are late to guarantee tasks are not lost if the worker crashes mid-processing
    task_acks_late=True,
)

# Automatically locate task modules inside worker package
celery_app.autodiscover_tasks(["app.worker"])

