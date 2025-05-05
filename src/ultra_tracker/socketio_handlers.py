
from .chat import get_recent_messages, save_message
from .database import ChatMessage
from flask import session
import datetime



def register_socketio_handlers(socketio, app):
    @socketio.on("connect")
    def handle_connect():
        for msg in get_recent_messages(limit=1000):
            socketio.emit("message", msg)


    @socketio.on("message")
    def handle_message(msg_text):
        username = session.get("username", "Anonymous")
        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.isoformat()
        msg_json = {
            "username": username,
            "text": msg_text,
            "timestamp": timestamp_str,
        }
        save_message(ChatMessage(username=username, text=msg_text, timestamp=timestamp))
        socketio.emit("message", msg_json)
