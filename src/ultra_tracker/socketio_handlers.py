
from .chat import CHAT_HISTORY, save_history
from flask import session
import datetime



def register_socketio_handlers(socketio, app):
    @socketio.on("connect")
    def handle_connect():
        for msg in CHAT_HISTORY:
            socketio.emit("message", msg)


    @socketio.on("message")
    def handle_message(msg_text):
        username = session.get("username", "Anonymous")
        msg = {
            "username": username,
            "text": msg_text,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        CHAT_HISTORY.append(msg)
        save_history(app)
        socketio.emit("message", msg)
