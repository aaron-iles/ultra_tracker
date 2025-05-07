#!/usr/bin/env python3

import datetime

from flask import session

from .chat import get_recent_messages, save_message
from .database import ChatMessage


def register_socketio_handlers(socketio) -> None:
    """
    This function is a helper to register the socketio handlers after the application has been
    created.

    :param SocketIO socketio: A SocketIO object created from the application.
    :return None:
    """
    @socketio.on("connect")
    def handle_connect() -> None:
        """
        A handler to populate the messages board when the socket is connected.

        :return None:
        """
        for msg in get_recent_messages(limit=1000):
            socketio.emit("message", msg)
        return

    @socketio.on("message")
    def handle_message(message_text: str) -> None:
        """
        A handler to push the message to the board when a message is sent by a user as well as to
        save the message to the database.

        :param str message_text: The message content.
        :return None:
        """
        username = session.get("username", "Anonymous")
        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.isoformat()
        msg_json = {
            "username": username,
            "text": message_text,
            "timestamp": timestamp_str,
        }
        save_message(ChatMessage(username=username, text=message_text, timestamp=timestamp))
        socketio.emit("message", msg_json)
        return
