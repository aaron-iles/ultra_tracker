#!/usr/bin/env python3


import logging
import warnings
from flask_socketio import SocketIO, send
import flask


__all__ = ["create_app"]


def create_app(session):
    app = flask.Flask(__name__)

    from .api import blueprint
    app.register_blueprint(blueprint)

    socketio = SocketIO(app)

    @app.teardown_request
    def remove_session(exception=None):
        session.remove()
        return

    return app, socketio
