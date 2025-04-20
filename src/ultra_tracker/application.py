#!/usr/bin/env python3


import logging
import warnings
from flask_socketio import SocketIO, send
import flask
from .socketio_handlers import register_socketio_handlers


__all__ = ["create_app"]


def create_app(session):
    app = flask.Flask(__name__)

    from .api import blueprint
    app.register_blueprint(blueprint)

    socketio = SocketIO(app)
    register_socketio_handlers(socketio, app)

    @app.teardown_request
    def remove_session(exception=None):
        session.remove()
        return

    return app, socketio
