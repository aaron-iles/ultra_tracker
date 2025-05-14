#!/usr/bin/env python3


import logging

from flask_socketio import SocketIO


__all__ = ["socketio"]

log = logging.getLogger(__name__)

socketio = SocketIO()
