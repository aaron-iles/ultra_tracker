#!/usr/bin/env python3


import datetime
import logging
import sys

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# Get a pointer to the module instance
this = sys.modules[__name__]
# Assign a var to the module itself. This allows access to the module-level variable from any other module
this.engine = None
this.session = None
Base = declarative_base()


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


# TODO: Add pings to the database
class Ping(Base):
    __tablename__ = "pings"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    raw_data = Column(JSON, nullable=False)


def connect(path: str) -> None:
    """
    Connects to the database to establish an engine and database session that will be defined at the
    module level to be used across the package.

    :param str path: The path to the database including the protocol.
    :return None:
    """
    # First check if the engine has already been initialized.
    if not this.engine:
        this.engine = create_engine(path)
    session_factory = sessionmaker(bind=this.engine)
    this.session = scoped_session(session_factory)
    Base.metadata.create_all(this.engine)
    return
