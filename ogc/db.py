import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.sql import func

import alembic.command
import alembic.config

DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_NAME = os.environ.get("POSTGRES_DB", "ogc")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    inspect
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    scoped_session,
    sessionmaker
)

Base = declarative_base()

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    name = Column(String(255))
    slug = Column(String(255), unique=True)
    created = Column(DateTime(), server_default=func.now())

    extra = Column(JSON(), nullable=True)
    nodes = relationship(
        "Node", back_populates="user", cascade="all, delete-orphan"
    )

class Node(Base):
    __tablename__ = "node"
    id = Column(Integer, primary_key=True)
    instance_name = Column(Text())
    instance_id = Column(Text())
    instance_state = Column(Text())
    username = Column(Text())
    public_ip = Column(Text())
    private_ip = Column(Text())
    ssh_public_key = Column(Text())
    ssh_private_key = Column(Text())
    provider = Column(Text())
    scripts = Column(Text())
    tags = Column(ARRAY(String), nullable=True)
    artifacts = Column(Text(), nullable=True)
    remote_path = Column(Text(), nullable=True)
    include = Column(ARRAY(String), nullable=True)
    exclude = Column(ARRAY(String), nullable=True)
    ports = Column(ARRAY(String), nullable=True)
    created = Column(DateTime(), server_default=func.now())

    # Store layout config here for easier reference
    layout = Column(JSON())
    extra = Column(JSON(), nullable=True)
    
    actions = relationship(
        "Actions", back_populates="node", cascade="all, delete-orphan"
    )

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="nodes")

    def __repr__(self):
        return f"Node(id={self.id!r}, user={self.user.name!r})"

class Actions(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True)
    exit_code = Column(Integer())
    out = Column(Text())
    error = Column(Text(), nullable=True)
    command = Column(Text(), nullable=True)
    node_id = Column(Integer, ForeignKey("node.id"), nullable=False)
    node = relationship("Node", back_populates="actions")
    created = Column(DateTime(), server_default=func.now())
    extra = Column(JSON(), nullable=True)

def connect():
    """Return a db connection"""
    db_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    return create_engine(db_string, echo=False, future=True)

def session(engine):
    _session = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=True, expire_on_commit=False))
    return _session()

def createtbl(engine):
    """Create db tables"""
    Base.metadata.create_all(engine)

def droptbl(engine):
    """Create db tables"""
    Base.metadata.drop_all(engine)

def model_as_dict(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}

def migrate():
    # retrieves the directory that *this* file is in
    migrations_dir = Path(__file__).parent.parent / 'alembic'
    # this assumes the alembic.ini is also contained in this same directory
    config_file = migrations_dir.parent / "alembic.ini"

    config = alembic.config.Config(file_=str(config_file))
    config.set_main_option("script_location", str(migrations_dir))

    # upgrade the database to the latest revision
    alembic.command.upgrade(config, "head")    


# Template helpers
def by_tag(context, tag):
    """Returns rows by tags"""
    with session(connect()) as _session:
        return _session.query(Node).filter(Node.tags.contains([tag]))


def by_name(context, name):
    """Returns rows by instance name"""
    with session(connect()) as _session:
        return _session.query(Node).filter_by(instance_name=name).one()


def by_id(context, id):
    """Returns rows by row id"""
    with session(connect()) as _session:
        return _session.query(Node).filter_by(id=id).one()
