from celery import Celery

celery_app = Celery(
    "ai_tasks",
    broker="redis://localhost:6379/0",  # Redis sebagai message broker
    backend="redis://localhost:6379/0"  # Redis sebagai result backend (opsional)
)
