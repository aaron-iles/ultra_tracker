#!/usr/bin/env python3


import logging

from flask_socketio import SocketIO

__all__ = ["socketio"]

logger = logging.getLogger(__name__)

socketio = SocketIO(async_mode="gevent")
