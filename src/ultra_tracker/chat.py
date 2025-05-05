#!/usr/bin/env python3


import datetime
import os
import json
from datetime import datetime
from . import database






def get_recent_messages(limit=10000):
    """Return the most recent chat messages from the database."""
    messages = (
        database.session.query(database.ChatMessage)
        .order_by(database.ChatMessage.timestamp.asc())
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
    database.session.close()
    return result


def save_message(msg: dict):
    database.session.add(msg)
    database.session.commit()
    #session.refresh(msg)
    database.session.close()
    return
