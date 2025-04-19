#!/usr/bin/env python3


import datetime
import logging
import sys
from urllib.parse import urlparse

import sqlalchemy
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


class Ping(Base):
    __tablename__ = "pings"

    id = Column(Integer, primary_key=True)
    data = Column(JSON, nullable=False)


def connect(path: str):
    if not this.engine:
        this.engine = sqlalchemy.create_engine(path)
    session_factory = sessionmaker(bind=this.engine)
    this.session = scoped_session(session_factory)
    Base.metadata.create_all(this.engine)
    return
