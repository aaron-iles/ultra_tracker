#!/usr/bin/env python3

import eventlet
import hashlib
import json
import logging
import time

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
import yaml
from ..database_utils import get_all_pings

logger = logging.getLogger(__name__)
URL_PREFIX = "/"
blueprint = Blueprint("root", __name__)


@blueprint.route("/", methods=["GET"])
def render_stats_page():
    """
    Renders the webpage for the race statistics and monitoring.

    :return tuple: The rendered HTML page.
    """
    race = current_app.config["UT_RACE"]
    return render_template("stats.html", **race.html_stats)


@blueprint.route("/course", methods=["GET"])
def render_course_page():
    """ """
    race = current_app.config["UT_RACE"]
    return render_template("course.html", **race.html_stats)


@blueprint.route("/map", methods=["GET"])
def render_map_page():
    """ """
    race = current_app.config["UT_RACE"]
    return render_template("map.html", **race.html_stats)


@blueprint.route("/profile", methods=["GET"])
def render_profile_page():
    """ """
    race = current_app.config["UT_RACE"]
    return render_template("profile.html", **race.html_stats)


@blueprint.route("/admin", methods=["GET"])
def render_admin_page():
    """ """
    if not session.get("logged_in"):
        return redirect(url_for("logs.login"))

    log_handler = next((h for h in logging.root.handlers if h.name == "InMemoryLogHandler"), None)

    if request.headers.get("Accept") == "text/event-stream":

        @stream_with_context
        def event_stream():
            # Bust proxy buffers + show something instantly
            yield ":" + (" " * 2048) + "\n"
            yield "event: hello\ndata: connected\n\n"
            seen = 0
            try:
                while True:
                    logs = log_handler.get_logs()
                    if len(logs) > seen:
                        for line in logs[seen:]:
                            yield f"data: {line}\n\n"
                        seen = len(logs)
                    else:
                        # Flush output even if no new logs
                        yield "event: ping\ndata: keepalive\n\n"
                    eventlet.sleep(1)
            except GeneratorExit:
                return

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    all_pings = get_all_pings()
    position_report_pings = sum(1 for p in all_pings if p.get("message_code") in {"Position Report"})

    # Convert each ping (dict) to YAML-formatted string
    ping_yaml_strings = [yaml.dump(ping, default_flow_style=False, sort_keys=False) for ping in all_pings]
    race = current_app.config["UT_RACE"]
    return render_template("admin_dashboard.html", ping_yamls=ping_yaml_strings, **race.html_stats, operational_state="running", position_report_pings=position_report_pings, pings_received=len(all_pings))


@blueprint.route("/raw", methods=["GET"])
def render_raw_page():
    """ """
    race = current_app.config["UT_RACE"]
    return render_template("raw.html", **race.html_stats)


@blueprint.route("/", methods=["POST"])
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
