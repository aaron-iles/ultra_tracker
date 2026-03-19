#!/usr/bin/env python3

import json
import logging

from flask import (
    Blueprint,
    current_app,
    request,
)

logger = logging.getLogger(__name__)
URL_PREFIX = "/"
blueprint = Blueprint("root", __name__)


@blueprint.route("/ping", methods=["POST"])
def post_data():
    """
    Receives a ping from the tracker, updates the race object, and logs information.

    :return tuple: The HTTP response.
    """
    if request.headers.get("x-outbound-auth-token") != current_app.config["UT_GARMIN_API_TOKEN"]:
        logger.error("Invalid or missing auth token in {request.headers}")
        return "Invalid or missing auth token", 401
    content_length = request.headers.get("Content-Length", 0)
    if not content_length:
        logger.error("Content-Length header is missing or zero")
        return "Content-Length header is missing or zero", 411
    payload = request.get_data(as_text=True)
    with open(f"{current_app.config['UT_DATA_DIR']}/post_log.txt", "a", encoding="ascii") as file:
        file.write(f"{payload}\n")
    current_app.config["UT_RACE"].ingest_ping(json.loads(payload))
    return "OK", 200
