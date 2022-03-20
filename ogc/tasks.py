from .celery import app

@app.task
def do_provision():
    print("im provisioning")
