import os
from atexit import register

import dill
from celery import Celery
from kombu.serialization import pickle_loads, pickle_protocol, registry
from kombu.utils.encoding import str_to_bytes

CELERY_BROKER_URL = (os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)


def register_dill():
    def encode(obj, dumper=dill.dumps):
        return dumper(obj, protocol=pickle_protocol)

    def decode(s):
        return pickle_loads(str_to_bytes(s), load=dill.load)

    registry.register(
        name="dill",
        encoder=encode,
        decoder=decode,
        content_type="application/x-python-serialize",
        content_encoding="binary",
    )


register_dill()

app = Celery(
    "ogc",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    task_serializer="dill",
    result_serializer="dill",
    accept_content=["dill"],
    include=["ogc.tasks"],
)

if __name__ == "__main__":
    app.start()
