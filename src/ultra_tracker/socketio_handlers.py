
from .chat import get_recent_messages, save_message
from flask import session
import datetime



def register_socketio_handlers(socketio, app):
    @socketio.on("connect")
    def handle_connect():
        for msg in get_recent_messages(limit=100):
            socketio.emit("message", msg)


    @socketio.on("message")
    def handle_message(msg_text):
        username = session.get("username", "Anonymous")
        msg = {
            "username": username,
            "text": msg_text,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        save_message(msg)
        socketio.emit("message", msg)






