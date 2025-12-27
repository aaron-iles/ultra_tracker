#!/usr/bin/env python3


import datetime
import json
import os

from . import database
from .models import tracker
from .ut_socket import socketio

# TODO move these to the database.py file ??


def get_all_pings() -> list:
    """ """
    pings = database.session.query(database.Ping).order_by(database.Ping.timestamp.asc()).all()
    result = [ping.raw_data for ping in pings]
    database.session.close()
    return result


def save_ping(ping) -> None:
    """ """
    db_ping = database.Ping(raw_data=ping.for_database, timestamp=ping.timestamp)
    database.session.add(db_ping)
    database.session.commit()
    database.session.close()
    return
