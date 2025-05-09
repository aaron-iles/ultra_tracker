#!/usr/bin/env python3

import hashlib
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
    """
    """
    race = current_app.config["UT_RACE"]
    return render_template("course.html", **race.html_stats)






@blueprint.route("/map", methods=["GET"])
def render_map_page():
    """
    """
    race = current_app.config["UT_RACE"]
    return render_template("map.html", **race.html_stats)


@blueprint.route("/profile", methods=["GET"])
def render_profile_page():
    """
    """
    race = current_app.config["UT_RACE"]
    return render_template("profile.html", **race.html_stats)


@blueprint.route("/raw", methods=["GET"])
def render_raw_page():
    """
    """
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


