import datetime

from peewee import *

DATABASE = PostgresqlDatabase(
    "ogc", user="postgres", password="postgres", host="localhost"
)


class BaseModel(Model):
    class Meta:
        database = DATABASE

    created = DateTimeField(default=datetime.datetime.utcnow)


class NodeModel(BaseModel):
    uuid = TextField()
    instance_name = TextField()
    instance_id = TextField()
    instance_state = TextField()
    username = CharField()
    public_ip = TextField()
    private_ip = TextField()
    ssh_public_key = TextField()
    ssh_private_key = TextField()
    provider = TextField()
    scripts = TextField()


def connect():
    """Create db tables"""
    DATABASE.connect()
    DATABASE.create_tables([NodeModel])
