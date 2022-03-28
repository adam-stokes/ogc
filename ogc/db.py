import os
from typing import Text

from sqlalchemy import create_engine

DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_NAME = os.environ.get("POSTGRES_DB", "ogc")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    scoped_session,
    sessionmaker
)

Base = declarative_base()


class Node(Base):
    __tablename__ = "node"
    id = Column(Integer, primary_key=True)
    uuid = Column(Text())
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

    actions = relationship(
        "Actions", back_populates="node", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"Node(id={self.id!r})"


class Actions(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True)
    exit_code = Column(Integer())
    out = Column(Text())
    error = Column(Text(), nullable=True)
    command = Column(Text(), nullable=True)
    node_id = Column(Integer, ForeignKey("node.id"), nullable=False)
    node = relationship("Node", back_populates="actions")


def connect():
    """Create db tables"""
    db_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    engine = create_engine(db_string, echo=False, future=True)
    Base.metadata.create_all(engine)
    _session = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=True, expire_on_commit=False))
    return _session()


# Template helpers
def by_tag(context, tag):
    """Returns rows by tags"""
    session = connect()
    return session.query(Node).filter(Node.tags.contains([tag]))


def by_name(context, name):
    """Returns rows by instance name"""
    session = connect()
    return session.query(Node).filter_by(instance_name=name).one()


def by_id(context, id):
    """Returns rows by row id"""
    session = connect()
    return session.query(Node).filter_by(id=id).one()
