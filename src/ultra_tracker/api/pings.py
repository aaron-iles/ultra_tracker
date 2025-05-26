#!/usr/bin/env python3

import hashlib
import logging
import time

import eventlet
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
    all_pings = get_all_pings()
    return render_template("pings.html", all_pings=all_pings)
