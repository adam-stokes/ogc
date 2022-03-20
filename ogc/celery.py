from celery import Celery

app = Celery('ogc',
            broker='redis://localhost:6379',
            backend='redis://localhost:6379',
            task_serializer='json',
            result_serializer='json',
            accept_content=['application/json'],
            include=['ogc.tasks'])

if __name__ == "__main__":
    app.start()