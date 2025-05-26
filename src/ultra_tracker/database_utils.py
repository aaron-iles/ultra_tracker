#!/usr/bin/env python3


import datetime
import json
import os

from . import database
from .models import tracker
from .ut_socket import socketio

# TODO move these to the database.py file ??


def send_bot_message(message_text: str):
    username = "UT Bot"
    timestamp = datetime.datetime.now()
    timestamp_str = timestamp.isoformat()
    msg_json = {
        "username": username,
        "text": message_text,
        "timestamp": timestamp_str,
    }
    save_message(database.ChatMessage(username=username, text=message_text, timestamp=timestamp))
    socketio.emit("message", msg_json)


def get_recent_messages(limit: int) -> list:
    """
    Return the most recent chat messages from the database up to the provided limit.

    :param int limit: The number of messages to return.
    :return list: The list of messages (as dicts) from the database.
    """
    messages = (
        database.session.query(database.ChatMessage)
        .order_by(database.ChatMessage.timestamp.asc())
        .limit(limit)
        .all()
    )
    result = [
        {"username": msg.username, "text": msg.text, "timestamp": msg.timestamp.isoformat()}
        for msg in messages
    ]
    database.session.close()
    return result


def save_message(message: database.ChatMessage) -> None:
    """
    Saves a ChatMessage object to the datbase.

    :param database.ChatMessage message: A ChatMessage object.
    :return None:
    """
    database.session.add(message)
    database.session.commit()
    database.session.close()
    return



def get_all_pings() -> list:
    """
    """
    pings = (
        database.session.query(database.Ping)
        .order_by(database.Ping.timestamp.desc())
        .all()
    )
    result = [ping.raw_data for ping in pings]
    database.session.close()
    return result


def save_ping(ping) -> None:
    """
    """
    db_ping = database.Ping(raw_data=ping.as_json_safe, timestamp=ping.timestamp)
    database.session.add(db_ping)
    database.session.commit()
    database.session.close()
    return




