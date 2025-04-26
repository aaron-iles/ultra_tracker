#!/usr/bin/env python3


import datetime
import os
import json
from datetime import datetime
from .database import ChatMessage, session






def get_recent_messages(limit=10000):
    """Return the most recent chat messages from the database."""
    messages = (
        session.query(ChatMessage)
        .order_by(ChatMessage.timestamp.asc())
        .limit(limit)
        .all()
    )
    result = [
        {
            "username": msg.username,
            "text": msg.text,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]
    session.close()
    return result


def save_message(msg: dict):
    session.add(msg)
    session.commit()
    #session.refresh(msg)
    session.close()
    return
