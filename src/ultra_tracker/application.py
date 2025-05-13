#!/usr/bin/env python3


import logging

import flask
from flask_socketio import SocketIO

from .socketio_handlers import register_socketio_handlers
from . import api

__all__ = ["create_app", "socketio"]

log = logging.getLogger(__name__)

socketio = SocketIO()


def create_app() -> tuple:
    """
    Creates the Flask application and socketio object to be used elsewhere in the package.

    :return tuple: The app and socketio objects.
    """
    log.info(f"creating app {__name__}")
    app = flask.Flask(__name__)
    app.url_map.strict_slashes = False
    log.info("registering blueprints")
    app.register_blueprint(api.chat.blueprint, url_prefix=api.chat.URL_PREFIX)
    app.register_blueprint(api.logs.blueprint, url_prefix=api.logs.URL_PREFIX)
    app.register_blueprint(api.race.blueprint, url_prefix=api.race.URL_PREFIX)
    log.info(f"registering SocketIO handlers")
    socketio.init_app(app)
    register_socketio_handlers(socketio)
    return app
