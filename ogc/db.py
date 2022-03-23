import datetime
import os

from peewee import *
from playhouse.postgres_ext import *

DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_NAME = os.environ.get("POSTGRES_DB", "ogc")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
DATABASE = PostgresqlExtDatabase(
    DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
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
    tags = ArrayField(CharField)


class NodeActionResult(BaseModel):
    """Results of ScriptDeployments and arbitrary commands stored here"""

    exit_code = IntegerField()
    out = TextField()
    error = TextField(null=True)
    node = ForeignKeyField(NodeModel, backref="actions", on_delete="CASCADE")


def connect():
    """Create db tables"""
    DATABASE.connect(reuse_if_open=True)
    DATABASE.create_tables([NodeModel, NodeActionResult])


# Template helpers
def by_tag(context, tag):
    """Returns rows by tags"""
    connect()
    return NodeModel.select().where(NodeModel.tags.contains(tag))


def by_name(context, name):
    """Returns rows by instance name"""
    connect()
    return NodeModel.get(NodeModel.instance_name == name)


def by_id(context, id):
    """Returns rows by row id"""
    connect()
    return NodeModel.get(NodeModel.id == id)
