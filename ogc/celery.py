import os

from celery import Celery

CELERY_BROKER_URL = (os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

app = Celery(
    "ogc_provision",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    include=["ogc.tasks"],
)

if __name__ == "__main__":
    app.start()
