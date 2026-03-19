#!/usr/bin/env python3


import logging

import flask

from . import api
from .ut_socket import socketio

__all__ = ["create_app"]

logger = logging.getLogger(__name__)


def create_app() -> tuple:
    """
    Creates the Flask application and socketio object to be used elsewhere in the package.

    :return tuple: The app and socketio objects.
    """
    logger.info(f"creating app {__name__}")
    app = flask.Flask(__name__)
    app.url_map.strict_slashes = False
    logger.info("registering blueprints")
    app.register_blueprint(api.race.blueprint, url_prefix=api.race.URL_PREFIX)
    logger.info("registering SocketIO handlers")
    socketio.init_app(app)
    return app
