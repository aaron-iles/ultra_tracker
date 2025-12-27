#!/usr/bin/env python3

import hashlib
import logging
import time

import eventlet
import yaml
from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)

from ..database_utils import get_all_pings

URL_PREFIX = "/pings"


blueprint = Blueprint("pings", __name__)


@blueprint.route("/")
def get_pings():
    if not session.get("logged_in"):
        return redirect(url_for("logs.login"))
    all_pings = get_all_pings()

    # Convert each ping (dict) to YAML-formatted string
    ping_yaml_strings = [
        yaml.dump(ping, default_flow_style=False, sort_keys=False) for ping in all_pings
    ]

    return render_template("pings.html", ping_yamls=ping_yaml_strings)
